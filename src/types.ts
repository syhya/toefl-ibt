export type SectionId = "reading" | "listening" | "writing" | "speaking";
export type Answer = string | string[] | Record<string, string | string[]>;
export type Timing = {
  readingCommon: number;
  readingSecond: number;
  listeningResponse: number;
  listeningAcademic: number;
  buildSentence: number;
  email: number;
  academicDiscussion: number;
  repeat: number[];
  interview: number;
};
export type Asset = {
  assetId?: string;
  url: string;
  alt?: string;
  role?: string;
  width?: number;
  height?: number;
  highResolution?: boolean;
  choiceId?: string;
};
export type StemBlock =
  | {
      type:
        | "instruction"
        | "title"
        | "paragraph"
        | "question"
        | "highlighted_sentence";
      text: string;
    }
  | {
      type: "message";
      sender?: string;
      recipient?: string;
      date?: string;
      subject?: string;
      paragraphs: string[];
    }
  | {
      type: "dialogue";
      turns: {
        speaker: string;
        text: string;
        avatarAssetIndex?: number;
      }[];
    }
  | {
      type: "list";
      items: string[];
      ordered?: boolean;
      marker?: "bullet" | "decimal" | "lower-alpha";
    }
  | { type: "form_diagram"; highlightedPosition: number }
  | {
      type: "table";
      caption?: string;
      headers: string[];
      rows: string[][];
      rowHeaders?: boolean;
    }
  | { type: "essential_visual"; assetIndex: number; alt: string };
export type Media = Asset & {
  kind?: string;
  scope?: string;
  instructions?: string;
  durationSeconds?: number;
  mediaType?: string;
  groupId?: string;
};
export type Blank = {
  id: string;
  number?: number;
  prefix?: string;
  suffix?: string;
  length?: number;
  missingLetters?: string;
  fullWord?: string;
  answer?: string;
  acceptedAnswers?: string[];
  auditStatus?: string;
  answerConflict?: unknown;
  sourceReferenceAnswer?: string;
};
export type Question = {
  id: string;
  number?: number;
  numberEnd?: number;
  type: string;
  interaction?: string;
  sourceImageContainsQuestionAndChoices?: boolean;
  taskType?: string;
  prompt?: string;
  passage?: string;
  passageTemplate?: string;
  context?: string;
  presentationSchema?: string;
  structuredContentStatus?: string;
  textCorrection?: { version: string; changedFields: number };
  sentencePrefix?: string;
  terminalPunctuation?: string;
  stemBlocks?: StemBlock[];
  transcript?: string;
  mediaSequence?: Media[];
  sourceVariant?: {
    id: string;
    notice: string;
    paperPrompt?: string;
    paperPage?: number;
    referenceUrl?: string;
    referencePage?: number;
  };
  displayTranscriptDuringPractice?: boolean;
  practiceMediaSequence?: Media[];
  choices?: { id: string; text: string }[];
  blanks?: Blank[];
  tokens?: string[];
  slots?: ({ id?: string; fixed?: string; text?: string } | string | null)[];
  fixedText?: string;
  answer?: Answer;
  sourceReferenceAnswer?: Answer;
  acceptedAnswers?: string[];
  sourceAnswerVariants?: unknown;
  answerConflict?: unknown;
  resolutionEvidence?: unknown;
  explanationConflict?: unknown;
  explanation?:
    | string
    | {
        origin: "source" | "local_assistance" | "unavailable";
        label: string;
        text: string;
        evidence?: string[];
        warnings?: string[];
        source?: { page?: number; materialId?: string; url?: string };
      };
  assets?: Asset[];
  sourceEvidenceAssets?: Asset[];
  audio?: Media;
  directionsAudio?: Media;
  source?: { page?: number; url?: string; materialId?: string };
  stimulusSource?: { page?: number; url?: string; materialId?: string };
  warnings?: string[];
  auditStatus?: string;
  grade?: { correct: number; total: number } | null;
};
export type Material = {
  id: string;
  assetId?: string;
  url: string | null;
  available?: boolean;
  name: string;
  path?: string;
  category?: string;
  kind: string;
  bytes?: number;
  supplemental?: boolean;
  examIds?: string[];
};
export type Exam = {
  sourceEdition?: string;
  id: string;
  title: string;
  family: string;
  supplemental?: boolean;
  strictEligible: boolean;
  adaptiveEligible?: boolean;
  scopedEligibility?: Record<string, boolean>;
  adaptiveEligibility?: Record<string, boolean>;
  resourcesOnly?: boolean;
  structuredReady?: boolean;
  structuredScreenCount?: number;
  sourceVerifiedStructuredCount?: number;
  structuredReviewOnlyCount?: number;
  essentialVisualCount?: number;
  warnings: string[];
  questionCount?: number;
  screenCount?: number;
  sourceMaterialIds?: string[];
  sections?: {
    id: SectionId;
    title?: string;
    questionCount?: number;
    taskTypes?: string[];
    modules?: {
      id: string;
      title: string;
      route?: string;
      questions?: Question[];
    }[];
  }[];
};
export type Catalog = {
  exams: Exam[];
  materials: Material[];
  stats?: Record<string, unknown>;
  excludedSystemFiles?: unknown[];
};
export type Stage = {
  id: string;
  section: SectionId;
  title: string;
  timer: "shared" | "item" | "untimed";
  seconds: number;
  timingBasis?: "official" | "source" | "local" | "untimed";
  responseWindows?: number[];
  partialModule?: boolean;
  questionCount: number;
  canBack: boolean;
  itemCount?: number;
  sectionItemCount?: number;
  sectionQuestionOffset?: number;
  currentQuestionUnitStart?: number;
  instructions?: string;
  hasDirectionsAudio?: boolean;
  directionsAudio?: Media;
  practiceAudio?: Media | Media[];
};
export type Integrity = { interrupted: boolean; events?: FlowEvent[] };
export type FlowEvent = {
  type?: string;
  action?: string;
  at?: number | string;
  detail?: unknown;
  details?: unknown;
};
export type Session = {
  sourceEdition?: string;
  id: string;
  requiresMicrophone?: boolean;
  scoreSnapshotStatus?: "pending" | "frozen" | "legacy-recomputed";
  scoreSnapshotCalculatedAt?: number | null;
  scoringEngineVersion?: string;
  examId: string;
  title: string;
  mode: "strict" | "practice";
  filtered?: boolean;
  scope: string;
  routeMode: string;
  route: string;
  status: "active" | "completed" | "abandoned";
  phase:
    "directions" | "audio" | "response" | "expired" | "paused" | "complete";
  stageIndex: number;
  questionIndex: number;
  revision: number;
  serverNow: number;
  deadline: number | null;
  remainingSeconds: number | null;
  stage?: Stage;
  question?: Question;
  answer?: Answer;
  questionMap?: {
    index: number;
    questionId: string;
    answered: boolean;
    flagged: boolean;
  }[];
  recordingSegments?: unknown[];
  recordingIntegrity?: RecordingIntegrity;
  integrity: Integrity;
  allowedActions: string[];
  progress?: {
    stageIndex: number;
    totalStages: number;
    questionIndex: number;
    totalQuestions: number;
  };
  mediaIndex?: number;
  mediaCount?: number;
  audioEarliestEnd?: number;
  startedAt?: string | number;
  updatedAt?: string | number;
  completedAt?: string | number;
  timing?: Timing;
  ruleVersion?: string;
  rulesVersion?: string;
  sourceVersionMatches?: boolean;
  canRecoverAudio?: boolean;
  audioRecoveryApplied?: boolean;
  allowPracticeAids?: boolean;
  practiceGroup?: PracticeGroupSummary;
};
export type PracticeGroupSummary = {
  groupId: string;
  groupContentId: string;
  moduleId: string;
  module: string;
  taskType: string;
  numberStart?: number;
  numberEnd?: number;
  screenCount: number;
  itemCount: number;
  sourceScreenCount?: number;
  unavailableCount?: number;
};
export type SessionSummary = Pick<
  Session,
  "id" | "examId" | "title" | "status" | "mode" | "scope" | "startedAt"
> & {
  integrity?: Integrity;
  isFullScope?: boolean;
  interrupted?: boolean;
  sourceVersionMatches?: boolean;
  canRecoverAudio?: boolean;
  audioRecoveryApplied?: boolean;
  practiceGroup?: PracticeGroupSummary;
};
export type Recording = {
  takeId: string;
  url: string;
  mimeType: string;
  size: number;
  segments: number | { id: string; index: number; size: number }[];
  completeSequence?: boolean;
  finalized?: boolean;
  expectedSegmentCount?: number;
  endedReason?: string;
  createdAt: string;
};
export type RecordingIntegrity = {
  status: "complete" | "pending" | "incomplete";
  expectedQuestionIds: string[];
  recordedQuestionIds: string[];
  missingQuestionIds: string[];
  incompleteTakes: {
    takeId: string;
    questionId: string;
    reason: string;
    expectedSegmentCount?: number;
    receivedSegmentCount?: number;
    missingIndices?: number[];
  }[];
};
export type Rating = { value: number; notes?: string };
export type Review = {
  session: Session;
  exam?: Exam;
  sections?: {
    id: SectionId;
    modules: { id: string; title: string; questions: Question[] }[];
  }[];
  answers: Record<string, Answer>;
  recordings: Record<string, Recording[]>;
  recordingIntegrity?: RecordingIntegrity;
  score: { correct: number; total: number; [key: string]: unknown };
  ratings: Record<string, Rating>;
  events: FlowEvent[];
};
export type EventInput = {
  action: string;
  requestId?: string;
  questionId?: string;
  answer?: Answer;
  value?: unknown;
  index?: number;
  reason?: string;
  details?: unknown;
  mediaIndex?: number;
};
