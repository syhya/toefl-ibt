/**
 * Visual observations of 14 distinct Pack 1-6 Daily Life materials and one
 * Student 1 notice matched between its supplied PDF and the live ETS Sampler.
 * No question text or answers are stored here. Evidence: docs/EXAM_UI_REFERENCE.md
 * and tmp/qa/reference-material-layout-evidence.json (source PDF/page/SHA-256).
 *
 * Pixel measurements use a 1000 px wide exam canvas. Font sizes and colors are
 * raster-derived approximations, not recovered ETS CSS tokens. widthPercent is
 * relative to the complete left half of that canvas, BEFORE its content padding.
 * Unknown material editions deliberately return undefined.
 */
export type ReferenceMaterialKind = "email" | "text-chain" | "notice";

export type ReferenceMaterialTheme =
  | "gold-square-serif"
  | "pale-square-sans"
  | "phone-gray"
  | "teal-square-scroll"
  | "mint-plain-labels"
  | "gold-square-scroll"
  | "aqua-square-scroll"
  | "teal-outline-post"
  | "orange-square-scroll"
  | "mint-rounded-serif"
  | "peach-rounded-sans"
  | "gold-rounded-serif"
  | "double-gray-notice";

export type ReferenceMaterialLayout = Readonly<{
  kind: ReferenceMaterialKind;
  theme: ReferenceMaterialTheme;
  frameColor: string;
  borderColor: string;
  borderWidthPx: number;
  borderRadiusPx: number;
  fontFamily: "serif" | "sans-serif";
  fontSizePx: number;
  lineHeight: number;
  /** Separate white label/value cells, a label on the frame, or no header. */
  headerStyle: "boxed-labels" | "plain-labels" | "none";
  bodyScroll: "classic" | "none";
  /** Total bordered body viewport height, including padding, at a 1000 px canvas. */
  bodyHeightPx?: number;
  bodyBackground: string;
  bodyBorderRadiusPx: number;
  framePaddingPx: number;
  bodyPaddingPx: number;
  /** Percent of the full left half of the exam canvas. */
  widthPercent: number;
  /** Source has a graphic that CSS metadata alone cannot replace. */
  requiresSourceVisual?: true;
}>;

const material = (layout: ReferenceMaterialLayout): ReferenceMaterialLayout =>
  Object.freeze(layout);

const PACK_1_EMAIL_21 = material({
  kind: "email", theme: "gold-square-serif",
  frameColor: "#e8ad40", borderColor: "#403b30", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "serif", fontSizePx: 16, lineHeight: 1.25,
  headerStyle: "boxed-labels", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 0, framePaddingPx: 9, bodyPaddingPx: 10, widthPercent: 92,
});

const PACK_1_EMAIL_23 = material({
  kind: "email", theme: "pale-square-sans",
  frameColor: "#e6efea", borderColor: "#605e57", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 11, lineHeight: 1.28,
  headerStyle: "boxed-labels", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 0, framePaddingPx: 6, bodyPaddingPx: 8, widthPercent: 89.7,
});

const PACK_1_TEXT_CHAIN = material({
  kind: "text-chain", theme: "phone-gray",
  frameColor: "#776e64", borderColor: "#4c2b18", borderWidthPx: 3,
  borderRadiusPx: 22, fontFamily: "sans-serif", fontSizePx: 11, lineHeight: 1.3,
  headerStyle: "none", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 17, framePaddingPx: 12, bodyPaddingPx: 8, widthPercent: 50.1,
});

const PACK_2_EMAIL_11 = material({
  kind: "email", theme: "teal-square-scroll",
  frameColor: "#066b70", borderColor: "#243f40", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 11, lineHeight: 1.3,
  headerStyle: "boxed-labels", bodyScroll: "classic", bodyBackground: "#ffffff",
  bodyHeightPx: 126,
  bodyBorderRadiusPx: 0, framePaddingPx: 7, bodyPaddingPx: 7, widthPercent: 71.3,
});

const PACK_2_EMAIL_13 = material({
  kind: "email", theme: "mint-plain-labels",
  frameColor: "#93d2ce", borderColor: "#4b6663", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 11, lineHeight: 1.3,
  headerStyle: "plain-labels", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 0, framePaddingPx: 8, bodyPaddingPx: 9, widthPercent: 65.5,
});

const PACK_2_EMAIL_15 = material({
  kind: "email", theme: "gold-square-scroll",
  frameColor: "#e3af4b", borderColor: "#8d773b", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 12, lineHeight: 1.22,
  headerStyle: "boxed-labels", bodyScroll: "classic", bodyBackground: "#ffffff",
  bodyHeightPx: 296,
  bodyBorderRadiusPx: 0, framePaddingPx: 8, bodyPaddingPx: 8, widthPercent: 83.6,
});

const PACK_3_EMAIL_11 = material({
  kind: "email", theme: "aqua-square-scroll",
  frameColor: "#60caca", borderColor: "#436665", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 12, lineHeight: 1.25,
  headerStyle: "boxed-labels", bodyScroll: "classic", bodyBackground: "#ffffff",
  bodyHeightPx: 131,
  bodyBorderRadiusPx: 0, framePaddingPx: 7, bodyPaddingPx: 7, widthPercent: 81.1,
});

const PACK_3_EMAIL_13 = material({
  kind: "email", theme: "teal-square-scroll",
  frameColor: "#04696c", borderColor: "#234947", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 12, lineHeight: 1.22,
  headerStyle: "boxed-labels", bodyScroll: "classic", bodyBackground: "#ffffff",
  bodyHeightPx: 257,
  bodyBorderRadiusPx: 0, framePaddingPx: 8, bodyPaddingPx: 8, widthPercent: 91.6,
});

const PACK_4_SOCIAL_POST = material({
  kind: "notice", theme: "teal-outline-post",
  frameColor: "#ffffff", borderColor: "#0a6563", borderWidthPx: 3,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 12, lineHeight: 1.5,
  headerStyle: "none", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 0, framePaddingPx: 16, bodyPaddingPx: 26, widthPercent: 76,
  requiresSourceVisual: true,
});

const PACK_4_EMAIL_13 = material({
  kind: "email", theme: "aqua-square-scroll",
  frameColor: "#60c2c1", borderColor: "#426563", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 12, lineHeight: 1.22,
  headerStyle: "boxed-labels", bodyScroll: "classic", bodyBackground: "#ffffff",
  bodyHeightPx: 296,
  bodyBorderRadiusPx: 0, framePaddingPx: 7, bodyPaddingPx: 7, widthPercent: 81.1,
});

const PACK_5_EMAIL_11 = material({
  kind: "email", theme: "orange-square-scroll",
  frameColor: "#fc7c1d", borderColor: "#b67936", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 12, lineHeight: 1.25,
  headerStyle: "boxed-labels", bodyScroll: "classic", bodyBackground: "#ffffff",
  bodyHeightPx: 135,
  bodyBorderRadiusPx: 0, framePaddingPx: 9, bodyPaddingPx: 7, widthPercent: 71.7,
});

const PACK_5_EMAIL_13 = material({
  kind: "email", theme: "mint-rounded-serif",
  frameColor: "#a6d2d1", borderColor: "#668280", borderWidthPx: 1,
  borderRadiusPx: 5, fontFamily: "serif", fontSizePx: 14, lineHeight: 1.08,
  headerStyle: "boxed-labels", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 0, framePaddingPx: 6, bodyPaddingPx: 8, widthPercent: 82.7,
});

const PACK_6_EMAIL_11 = material({
  kind: "email", theme: "peach-rounded-sans",
  frameColor: "#f9e2d2", borderColor: "#634838", borderWidthPx: 2,
  borderRadiusPx: 12, fontFamily: "sans-serif", fontSizePx: 12, lineHeight: 1.25,
  headerStyle: "boxed-labels", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 10, framePaddingPx: 8, bodyPaddingPx: 12, widthPercent: 80.3,
});

const PACK_6_EMAIL_13 = material({
  kind: "email", theme: "gold-rounded-serif",
  frameColor: "#f2cd90", borderColor: "#bc790a", borderWidthPx: 3,
  borderRadiusPx: 10, fontFamily: "serif", fontSizePx: 13, lineHeight: 1.1,
  headerStyle: "boxed-labels", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 0, framePaddingPx: 13, bodyPaddingPx: 7, widthPercent: 86.7,
});

// Student 1 PDF physical page 4. Live Sampler corroborates a ~356 x 168 px
// notice at a 1024 px canvas, two thin gray borders, a centered 14 px bold
// heading and an 11 px bold subheading. The theme owns the second inset border.
// Frame padding (8) plus body padding (14) gives the observed ~22 px text inset.
const STUDENT_1_DOUBLE_GRAY_NOTICE = material({
  kind: "notice", theme: "double-gray-notice",
  frameColor: "#ffffff", borderColor: "#777777", borderWidthPx: 1,
  borderRadiusPx: 0, fontFamily: "sans-serif", fontSizePx: 11, lineHeight: 1.28,
  headerStyle: "none", bodyScroll: "none", bodyBackground: "#ffffff",
  bodyBorderRadiusPx: 0, framePaddingPx: 8, bodyPaddingPx: 14, widthPercent: 70,
});

const layouts: Record<string, ReferenceMaterialLayout> = Object.create(null);
const group = (pack: number, first: number, last: number, layout: ReferenceMaterialLayout) => {
  for (let item = first; item <= last; item += 1) {
    layouts[`pack-${pack}-reading-m1-${item}`] = layout;
  }
};

group(1, 21, 22, PACK_1_EMAIL_21);
group(1, 23, 25, PACK_1_EMAIL_23);
group(1, 26, 28, PACK_1_TEXT_CHAIN);
group(2, 11, 12, PACK_2_EMAIL_11);
group(2, 13, 14, PACK_2_EMAIL_13);
group(2, 15, 17, PACK_2_EMAIL_15);
group(3, 11, 12, PACK_3_EMAIL_11);
group(3, 13, 15, PACK_3_EMAIL_13);
group(4, 11, 12, PACK_4_SOCIAL_POST);
group(4, 13, 15, PACK_4_EMAIL_13);
group(5, 11, 12, PACK_5_EMAIL_11);
group(5, 13, 15, PACK_5_EMAIL_13);
group(6, 11, 12, PACK_6_EMAIL_11);
group(6, 13, 15, PACK_6_EMAIL_13);
layouts["student-1-r1-11"] = STUDENT_1_DOUBLE_GRAY_NOTICE;
layouts["student-1-r1-12"] = STUDENT_1_DOUBLE_GRAY_NOTICE;

/** Only these supplemental ids have verified canonical Pack counterparts. */
export const PAID_CANONICAL_MATERIAL_IDS: Readonly<Record<string, string>> = Object.freeze({
  "paid-1-r1-21": "pack-1-reading-m1-21",
  "paid-1-r1-22": "pack-1-reading-m1-22",
  "paid-1-r1-23": "pack-1-reading-m1-23",
  "paid-1-r1-24": "pack-1-reading-m1-24",
  "paid-1-r1-25": "pack-1-reading-m1-25",
  "paid-1-r1-26": "pack-1-reading-m1-26",
  "paid-1-r1-27": "pack-1-reading-m1-27",
  "paid-1-r1-28": "pack-1-reading-m1-28",
  "paid-2-r1-11": "pack-2-reading-m1-11",
  "paid-2-r1-12": "pack-2-reading-m1-12",
  "paid-2-r1-13": "pack-2-reading-m1-13",
  "paid-2-r1-14": "pack-2-reading-m1-14",
  "paid-2-r1-15": "pack-2-reading-m1-15",
  "paid-2-r1-16": "pack-2-reading-m1-16",
  "paid-2-r1-17": "pack-2-reading-m1-17",
});

export const REFERENCE_MATERIAL_LAYOUTS: Readonly<Record<string, ReferenceMaterialLayout>> =
  Object.freeze(layouts);

export function referenceMaterialLayout(questionId?: string): ReferenceMaterialLayout | undefined {
  if (!questionId) return undefined;
  const canonical = Object.hasOwn(PAID_CANONICAL_MATERIAL_IDS, questionId)
    ? PAID_CANONICAL_MATERIAL_IDS[questionId]
    : questionId;
  return REFERENCE_MATERIAL_LAYOUTS[canonical];
}
