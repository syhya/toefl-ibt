import {Blob as NodeBlob} from 'node:buffer';
import {IDBFactory} from 'fake-indexeddb';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {waitFor} from '@testing-library/react';

const apiMock=vi.hoisted(()=>vi.fn());
vi.mock('../../src/api',()=>({api:apiMock}));

beforeEach(()=>{
  vi.resetModules();
  apiMock.mockReset();
  vi.stubGlobal('indexedDB',new IDBFactory());
  vi.stubGlobal('Blob',NodeBlob);
});
const chunk=(index:number,text:string)=>({sessionId:'session-test',questionId:'speaking-one',takeId:'take-one',index,blob:new Blob([text]),mimeType:'audio/webm'});

describe('durable recording drafts',()=>{
  it('retains an offline segment and retries the same identity and bytes after reconnection',async()=>{
    const recording=await import('../../src/recording');
    apiMock.mockRejectedValueOnce(new Error('offline'));
    const errors=vi.fn();
    await recording.saveChunk(chunk(0,'HEADER'),errors);
    expect(errors).toHaveBeenCalled();
    expect(await recording.pendingRecordings()).toBe(1);
    const originalURL=apiMock.mock.calls[0][0];
    apiMock.mockResolvedValueOnce({ok:true});
    expect(await recording.retryRecordings('session-test')).toBe(0);
    expect(apiMock.mock.calls[1][0]).toBe(originalURL);
    expect(await apiMock.mock.calls[1][1].body.text()).toBe('HEADER');
  });

  it('preserves take IDs and sequence indices when chunks arrive out of order and survive a module reload',async()=>{
    let recording=await import('../../src/recording');
    apiMock.mockRejectedValue(new Error('offline'));
    await Promise.all([recording.saveChunk(chunk(1,'BODY'),vi.fn()),recording.saveChunk(chunk(0,'HEADER'),vi.fn())]);
    expect(await recording.pendingRecordings()).toBe(2);
    const originalIds=new Set(apiMock.mock.calls.map(([url])=>new URL(url,'http://localhost').searchParams.get('segmentId')));
    vi.resetModules();
    recording=await import('../../src/recording');
    apiMock.mockReset();apiMock.mockResolvedValue({ok:true});
    expect(await recording.retryRecordings('session-test')).toBe(0);
    const restored=await Promise.all(apiMock.mock.calls.map(async([url,options])=>{
      const params=new URL(url,'http://localhost').searchParams;
      expect(params.get('takeId')).toBe('take-one');
      expect(originalIds.has(params.get('segmentId'))).toBe(true);
      return {index:Number(params.get('index')),text:await options.body.text()};
    }));
    expect(restored.sort((a,b)=>a.index-b.index).map(item=>item.text).join('')).toBe('HEADERBODY');
  });

  it('waits for queued uploads before reporting recording flush complete',async()=>{
    const recording=await import('../../src/recording');
    let release!:()=>void;
    apiMock.mockImplementation(()=>new Promise(resolve=>{release=()=>resolve({ok:true});}));
    void recording.saveChunk(chunk(0,'FINAL'),vi.fn());
    await waitFor(()=>expect(apiMock).toHaveBeenCalledTimes(1));
    let done=false;
    const flushing=recording.flushRecordings().then(()=>{done=true;});
    await Promise.resolve();
    expect(done).toBe(false);
    release();
    await flushing;
    expect(done).toBe(true);
    expect(await recording.pendingRecordings()).toBe(0);
  });

  it('retains an in-memory fallback if both IndexedDB and the local server are unavailable',async()=>{
    vi.stubGlobal('indexedDB',{open:()=>{throw new Error('storage denied');}});
    const recording=await import('../../src/recording');
    apiMock.mockRejectedValue(new Error('offline'));
    const errors=vi.fn();
    await recording.saveChunk(chunk(0,'UNSAVED_AUDIO'),errors);
    expect(errors.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(await recording.pendingRecordings()).toBe(1);
    apiMock.mockResolvedValue({ok:true});
    expect(await recording.retryRecordings()).toBe(0);
  });

  it('waits for the recorder stop event and its delayed final chunk before finishing',async()=>{
    const recording=await import('../../src/recording');
    class Recorder extends EventTarget {
      state='recording';
      stop=vi.fn(()=>{this.state='inactive';});
    }
    const recorder=new Recorder();
    recording.trackRecorder(recorder as unknown as MediaRecorder);
    let uploaded!:()=>void;
    apiMock.mockImplementation(()=>new Promise(resolve=>{uploaded=()=>resolve({ok:true});}));
    let finished=false;
    const completion=recording.stopRecorders().then(recording.flushRecordings).then(()=>{finished=true;});
    expect(recorder.stop).toHaveBeenCalledTimes(1);
    await Promise.resolve();
    expect(finished).toBe(false);
    // MediaRecorder emits dataavailable before stop, even if that task arrives late.
    void recording.saveChunk(chunk(0,'DELAYED_FINAL_SEGMENT'),vi.fn());
    recorder.dispatchEvent(new Event('stop'));
    await waitFor(()=>expect(apiMock).toHaveBeenCalledTimes(1));
    expect(finished).toBe(false);
    uploaded();
    await completion;
    expect(finished).toBe(true);
    expect(await recording.pendingRecordings()).toBe(0);
  });

  it('persists finalization offline and restores the same expected count and end reason after reload',async()=>{
    let recording=await import('../../src/recording');
    apiMock.mockRejectedValue(new Error('offline'));
    const final={sessionId:'session-test',questionId:'speaking-one',takeId:'take-one',segmentCount:3,endedReason:'time-limit',mimeType:'audio/webm'};
    await recording.saveFinalization(final,vi.fn());
    expect(await recording.pendingRecordings()).toBe(1);
    const originalURL=apiMock.mock.calls[0][0];
    const originalBody=apiMock.mock.calls[0][1].body;
    expect(originalURL).toBe('/api/sessions/session-test/recordings/takes/take-one/finalize');
    expect(JSON.parse(originalBody)).toEqual({questionId:'speaking-one',segmentCount:3,endedReason:'time-limit',mimeType:'audio/webm'});
    vi.resetModules();
    recording=await import('../../src/recording');
    apiMock.mockReset();apiMock.mockResolvedValue({ok:true});
    expect(await recording.retryRecordings('session-test')).toBe(0);
    expect(apiMock.mock.calls[0][0]).toBe(originalURL);
    expect(apiMock.mock.calls[0][1].body).toBe(originalBody);
  });

  it('keeps the last chunk pending when finalization is acknowledged first',async()=>{
    const recording=await import('../../src/recording');
    let releaseTail!:()=>void;
    apiMock.mockImplementation((url:string)=>{
      if(url.endsWith('/finalize'))return Promise.resolve({take:{state:'missing_segments',expectedSegmentCount:2}});
      if(new URL(url,'http://localhost').searchParams.get('index')==='1')return new Promise(resolve=>{releaseTail=()=>resolve({ok:true});});
      return Promise.resolve({ok:true});
    });
    const first=recording.saveChunk(chunk(0,'HEADER'),vi.fn());
    const last=recording.saveChunk(chunk(1,'FINAL_BYTES'),vi.fn());
    const final=recording.saveFinalization({sessionId:'session-test',questionId:'speaking-one',takeId:'take-one',segmentCount:2,endedReason:'time-limit',mimeType:'audio/webm'},vi.fn());
    await first;await final;
    expect(await recording.pendingRecordings()).toBe(1);
    let flushed=false;
    const flush=recording.flushRecordings().then(()=>{flushed=true;});
    await Promise.resolve();
    expect(flushed).toBe(false);
    releaseTail();
    await last;await flush;
    expect(await recording.pendingRecordings()).toBe(0);
    const postedFinal=apiMock.mock.calls.find(([url])=>url.endsWith('/finalize'))!;
    expect(JSON.parse(postedFinal[1].body).segmentCount).toBe(2);
    const postedTail=apiMock.mock.calls.find(([url])=>!url.endsWith('/finalize')&&new URL(url,'http://localhost').searchParams.get('index')==='1')!;
    expect(await postedTail[1].body.text()).toBe('FINAL_BYTES');
  });
});
