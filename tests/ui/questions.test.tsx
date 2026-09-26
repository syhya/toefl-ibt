import React, {useState} from 'react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {AnswerInput} from '../../src/Questions';
import type {Answer, Question} from '../../src/types';

afterEach(cleanup);

function Editor({question, strict=false, disabled=false}:{question:Question;strict?:boolean;disabled?:boolean}) {
  const [value,setValue]=useState<Answer>();
  return <><AnswerInput question={question} value={value} onChange={setValue} disabled={disabled} strict={strict}/><output data-testid="answer">{JSON.stringify(value)}</output></>;
}
const sentence:Question={id:'sentence-1',type:'build_sentence',tokens:['the','the','extra'],slots:[{fixed:'We use'},{id:'one'},{id:'two'},{fixed:'.'}]};
const value=()=>JSON.parse(screen.getByTestId('answer').textContent||'null');

describe('sentence word-bank interaction',()=>{
  it('keeps equal words as distinct token indices and leaves extra words unused',async()=>{
    const user=userEvent.setup();
    render(<Editor question={sentence}/>);
    await user.click(screen.getByRole('button',{name:'Use word block 1: the'}));
    await user.click(screen.getByRole('button',{name:'Use word block 2: the'}));
    expect(value()).toEqual({tokenOrder:['0','1']});
    expect((screen.getByRole('button',{name:'Use word block 1: the'}) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole('button',{name:'Use word block 2: the'}) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole('button',{name:'Use word block 3: extra'}) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByText('We use')).toBeTruthy();
    expect(screen.getByText(/2 \/ 2 gaps filled/)).toBeTruthy();
  });

  it('supports keyboard selection, removing a filled gap and reusing its individual token',async()=>{
    const user=userEvent.setup();
    render(<Editor question={sentence}/>);
    await user.click(screen.getByRole('button',{name:'Use word block 1: the'}));
    await user.click(screen.getByRole('button',{name:'Use word block 2: the'}));
    await user.click(screen.getByRole('button',{name:'Gap 1: the. Click to remove.'}));
    expect(value()).toEqual({tokenOrder:['','1']});
    screen.getByRole('button',{name:'Use word block 1: the'}).focus();
    await user.keyboard('{Enter}');
    expect(value()).toEqual({tokenOrder:['0','1']});
    await user.click(screen.getByRole('button',{name:'Clear sentence'}));
    expect(value()).toEqual({tokenOrder:['','']});
  });

  it('drops a word by its index and ignores an unrelated drag payload',()=>{
    render(<Editor question={sentence}/>);
    const gap=screen.getByRole('button',{name:'Gap 2: empty'});
    const dragData=new Map<string,string>();
    const dataTransfer={setData:(format:string,data:string)=>dragData.set(format,data),getData:(format:string)=>dragData.get(format)||''};
    fireEvent.dragStart(screen.getByRole('button',{name:'Use word block 2: the'}),{dataTransfer});
    fireEvent.drop(gap,{dataTransfer});
    expect(value()).toEqual({tokenOrder:['','1']});
    fireEvent.drop(screen.getByRole('button',{name:'Gap 1: empty'}),{dataTransfer:{getData:()=> ''}});
    expect(value()).toEqual({tokenOrder:['','1']});
  });

  it('does not accept a token after the response input has been disabled',async()=>{
    const user=userEvent.setup();
    render(<Editor question={sentence} disabled/>);
    await user.click(screen.getByRole('button',{name:'Use word block 1: the'}));
    expect(value()).toBeNull();
  });

  it('moves a placed word to another gap and returns the displaced word to the bank',async()=>{
    const user=userEvent.setup();
    render(<Editor question={sentence}/>);
    await user.click(screen.getByRole('button',{name:'Use word block 1: the'}));
    await user.click(screen.getByRole('button',{name:'Use word block 3: extra'}));
    const filled=screen.getByRole('button',{name:'Gap 1: the. Click to remove.'});
    expect(filled.getAttribute('draggable')).toBe('true');
    const data=new Map<string,string>();
    const dataTransfer={setData:(format:string,payload:string)=>data.set(format,payload),getData:(format:string)=>data.get(format)||''};
    fireEvent.dragStart(filled,{dataTransfer});
    fireEvent.drop(screen.getByRole('button',{name:'Gap 2: extra. Click to remove.'}),{dataTransfer});
    fireEvent.dragEnd(filled,{dataTransfer});
    expect(value()).toEqual({tokenOrder:['','0']});
    expect((screen.getByRole('button',{name:'Use word block 1: the'}) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole('button',{name:'Use word block 3: extra'}) as HTMLButtonElement).disabled).toBe(false);
    await user.click(screen.getByRole('button',{name:'Gap 1: empty'}));
    await user.click(screen.getByRole('button',{name:'Use word block 3: extra'}));
    expect(value()).toEqual({tokenOrder:['2','0']});
    // A subsequent real click must still remove the word, even after a drag.
    await user.click(screen.getByRole('button',{name:'Gap 2: the. Click to remove.'}));
    expect(value()).toEqual({tokenOrder:['2','']});
  });

  it('places the captured pointer-dragged token into the hit-tested gap',()=>{
    class Pointer extends MouseEvent {
      pointerId:number;
      constructor(type:string,init:MouseEventInit&{pointerId?:number}={}){super(type,init);this.pointerId=init.pointerId||1;}
    }
    vi.stubGlobal('PointerEvent',Pointer);
    render(<Editor question={sentence}/>);
    const token=screen.getByRole('button',{name:'Use word block 2: the'});
    const gap=screen.getByRole('button',{name:'Gap 2: empty'});
    const hitTest=vi.fn(()=>gap);
    Object.defineProperty(document,'elementFromPoint',{configurable:true,value:hitTest});
    fireEvent.pointerDown(token,{button:0,pointerId:7,clientX:20,clientY:30});
    fireEvent.pointerMove(token,{button:0,pointerId:7,clientX:240,clientY:160});
    fireEvent.pointerUp(token,{button:0,pointerId:7,clientX:240,clientY:160});
    expect(hitTest).toHaveBeenCalledWith(240,160);
    expect(value()).toEqual({tokenOrder:['','1']});
  });

  it('rejects foreign-question pointer and HTML5 drops without triggering fallback placement',()=>{
    class Pointer extends MouseEvent {
      pointerId:number;
      constructor(type:string,init:MouseEventInit&{pointerId?:number}={}){super(type,init);this.pointerId=init.pointerId||1;}
    }
    vi.stubGlobal('PointerEvent',Pointer);
    render(<Editor question={sentence}/>);
    const token=screen.getByRole('button',{name:'Use word block 1: the'});
    const foreign=document.createElement('button');
    foreign.dataset.questionId='a-different-question';foreign.dataset.sentenceGap='0';
    Object.defineProperty(document,'elementFromPoint',{configurable:true,value:()=>foreign});
    fireEvent.pointerDown(token,{button:0,pointerId:9,clientX:10,clientY:10});
    fireEvent.pointerMove(token,{button:0,pointerId:9,clientX:180,clientY:120});
    fireEvent.pointerUp(token,{button:0,pointerId:9,clientX:180,clientY:120});
    fireEvent.click(token);
    expect(value()).toBeNull();
    fireEvent.drop(screen.getByRole('button',{name:'Gap 1: empty'}),{dataTransfer:{getData:()=>JSON.stringify({questionId:'a-different-question',index:0})}});
    expect(value()).toBeNull();
  });
});

describe('writing editor',()=>{
  it('keeps word count and undo/redo consistent without requiring 100 words to edit or submit',()=>{
    render(<Editor question={{id:'discussion',type:'academic_discussion'}}/>);
    const input=screen.getByRole('textbox',{name:'Your written response'}) as HTMLTextAreaElement;
    fireEvent.change(input,{target:{value:'First response'}});
    fireEvent.change(input,{target:{value:'First revised response'}});
    expect(value()).toBe('First revised response');
    expect(screen.getByText('3',{selector:'.editor-meta b'})).toBeTruthy();
    fireEvent.click(screen.getByRole('button',{name:'Undo'}));
    expect(value()).toBe('First response');
    fireEvent.click(screen.getByRole('button',{name:'Redo'}));
    expect(value()).toBe('First revised response');
    fireEvent.keyDown(input,{key:'z',ctrlKey:true});
    expect(value()).toBe('First response');
    expect(input.disabled).toBe(false);
    expect(input.getAttribute('spellcheck')).toBe('false');
  });

  it('blocks clipboard actions in strict writing while keeping native typing available',()=>{
    render(<Editor question={{id:'email',type:'email'}} strict/>);
    const input=screen.getByRole('textbox',{name:'Your written response'});
    expect(fireEvent.paste(input,{clipboardData:{getData:()=> 'external answer'}})).toBe(false);
    expect(fireEvent.copy(input)).toBe(false);
    expect(fireEvent.cut(input)).toBe(false);
    fireEvent.change(input,{target:{value:'My own answer'}});
    expect(value()).toBe('My own answer');
  });
});

it('renders source-verified sentence prefaces and final punctuation without adding answer gaps',()=>{
  const source:Question={id:'source-literals',type:'build_sentence',sentencePrefix:'Thanks.',terminalPunctuation:'?',tokens:['Are','you'],slots:[{id:'one'},{id:'two'}]};
  render(<Editor question={source}/>);
  const group=screen.getByRole('group',{name:'Sentence word slots'});
  expect(group.textContent).toContain('Thanks.');
  expect(group.textContent?.trim().endsWith('?')).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Use word block 1: Are'}));
  fireEvent.click(screen.getByRole('button',{name:'Use word block 2: you'}));
  expect(value()).toEqual({tokenOrder:['0','1']});
  expect(screen.getByText(/2 \/ 2 gaps filled/)).toBeTruthy();
  expect(source.slots).toEqual([{id:'one'},{id:'two'}]);
});
