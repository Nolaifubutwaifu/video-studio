import React, {useMemo} from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {resolveFont} from './fonts';
import type {CaptionStyle, Word} from './types';

type Chunk = {words: Word[]; start: number; end: number};

/**
 * Group words into the small on-screen bursts social captions use.
 *
 * Chunks break on the caption's word budget, but ALSO on sentence-ending
 * punctuation and on any real gap in speech -- otherwise a chunk spans a pause
 * and hangs on screen in silence, which reads as a stall.
 */
export const chunkWords = (
  words: Word[],
  maxWords: number,
  gapSec = 0.6,
): Chunk[] => {
  const chunks: Chunk[] = [];
  let current: Word[] = [];

  const flush = () => {
    if (!current.length) return;
    chunks.push({
      words: current,
      start: current[0].start,
      end: current[current.length - 1].end,
    });
    current = [];
  };

  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const prev = words[i - 1];
    if (prev && w.start - prev.end > gapSec) flush();
    current.push(w);
    if (current.length >= maxWords || /[.!?]$/.test(w.word)) flush();
  }
  flush();
  return chunks;
};

const applyCase = (text: string, mode: CaptionStyle['case']) => {
  if (mode === 'upper') return text.toUpperCase();
  if (mode === 'lower') return text.toLowerCase();
  return text;
};

export const Captions: React.FC<{words: Word[]; style: CaptionStyle}> = ({
  words,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const time = frame / fps;

  const chunks = useMemo(
    () => chunkWords(words, Math.max(1, style.maxWordsOnScreen)),
    [words, style.maxWordsOnScreen],
  );

  // A chunk stays up until the next one starts, so there is never a caption
  // gap mid-sentence; the last chunk lingers briefly instead of snapping off.
  const activeIndex = useMemo(() => {
    for (let i = chunks.length - 1; i >= 0; i--) {
      if (time >= chunks[i].start) return i;
    }
    return -1;
  }, [chunks, time]);

  if (activeIndex < 0) return null;

  const chunk = chunks[activeIndex];
  const next = chunks[activeIndex + 1];
  const visibleUntil = next ? next.start : chunk.end + 0.4;
  if (time > visibleUntil) return null;

  const fontSize = (style.sizePct / 100) * height;
  const strokeWidth = (style.stroke.widthPct / 100) * height;
  const fontFamily = resolveFont(style.font);

  const entered = spring({
    frame: frame - Math.round(chunk.start * fps),
    fps,
    config: {damping: 200, stiffness: 220, mass: 0.6},
    durationInFrames: Math.round(fps * 0.22),
  });

  // Exactly one word is active at a time. Whisper occasionally emits
  // overlapping word spans, and testing against each word's own range
  // independently then lights up two at once -- so pick the latest word that
  // has started and highlight only that one.
  let activeWord = -1;
  for (let i = 0; i < chunk.words.length; i++) {
    if (time >= chunk.words[i].start) activeWord = i;
  }

  const scale =
    style.enter === 'pop' ? interpolate(entered, [0, 1], [0.86, 1]) : 1;
  const opacity =
    style.enter === 'none' ? 1 : interpolate(entered, [0, 1], [0, 1]);

  return (
    <div
      style={{
        position: 'absolute',
        left: `${style.marginPct}%`,
        width: `${100 - style.marginPct * 2}%`,
        top: `${style.yPct}%`,
        transform: `translateY(-50%) scale(${scale})`,
        opacity,
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        alignItems: 'center',
        gap: `${fontSize * 0.22}px`,
        fontFamily,
        fontWeight: style.weight,
        fontSize,
        lineHeight: style.lineHeight,
        textAlign: 'center',
        // Stroke is painted UNDER the fill; without this the outline eats into
        // the letterforms and thin weights turn to mush at caption sizes.
        paintOrder: 'stroke fill',
        WebkitTextStrokeWidth: `${strokeWidth}px`,
        WebkitTextStrokeColor: style.stroke.color,
        textShadow: style.shadow ?? undefined,
      }}
    >
      {chunk.words.map((w, idx) => {
        const isActive =
          style.mode === 'word-highlight' && idx === activeWord;
        return (
          <span
            key={w.i}
            style={{
              color: isActive ? style.highlight : style.fill,
              background:
                isActive && style.highlightBox ? style.highlightBox : undefined,
              padding: style.highlightBox
                ? `0 ${fontSize * 0.12}px`
                : undefined,
              borderRadius: style.highlightBox ? fontSize * 0.12 : undefined,
              display: 'inline-block',
              // Nudge the active word up a touch -- the reference look is a
              // bounce, not just a colour swap.
              transform: isActive ? 'translateY(-2%)' : undefined,
            }}
          >
            {applyCase(w.word, style.case)}
          </span>
        );
      })}
    </div>
  );
};
