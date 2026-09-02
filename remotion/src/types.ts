export type Word = {
  i: number;
  word: string;
  key: string;
  start: number;   // seconds, on the RENDERED timeline (post-trim)
  end: number;
  prob?: number;
};

export type CaptionStyle = {
  /** word-highlight recolours one word at a time; phrase pops whole chunks. */
  mode: 'word-highlight' | 'phrase';
  font: string;
  weight: number;
  /** none keeps whatever the transcript produced. */
  case: 'upper' | 'lower' | 'none';
  /** Percent of video HEIGHT, so the look survives a resolution change. */
  sizePct: number;
  /** Vertical centre of the caption block, percent of height from the top. */
  yPct: number;
  maxWordsOnScreen: number;
  fill: string;
  highlight: string;
  /** Colour behind the active word. Omit for no highlight box. */
  highlightBox?: string | null;
  stroke: { color: string; widthPct: number };
  shadow?: string | null;
  enter: 'pop' | 'fade' | 'none';
  lineHeight: number;
  /** Horizontal padding as percent of width, keeps text off the bezel. */
  marginPct: number;
};

export type Profile = {
  name: string;
  format: { width: number; height: number; fps: number };
  pacing: {
    wpm: number;
    avg_shot_sec: number;
    cuts_per_min: number;
    max_silence_sec: number;
  };
  captions: CaptionStyle;
  graphics: {
    titleCard: boolean;
    titleCardSec: number;
    progressBar: boolean;
    progressBarColor: string;
  };
  audio: { lufs: number };
  grade?: { saturation: number; contrast: number } | null;
};

export type VideoProps = {
  videoSrc: string;      // path relative to public/
  words: Word[];
  profile: Profile;
  title?: string | null;
  durationInFrames: number;
};
