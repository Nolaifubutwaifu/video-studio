import React from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Captions} from './Captions';
import {resolveFont} from './fonts';
import type {VideoProps} from './types';

const TitleCard: React.FC<{title: string; seconds: number; font: string}> = ({
  title,
  seconds,
  font,
}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const total = Math.round(seconds * fps);
  if (frame > total) return null;

  // Hold, then fade out over the last third.
  const opacity = interpolate(
    frame,
    [0, 4, total * 0.66, total],
    [0, 1, 1, 0],
    {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'},
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        paddingTop: '14%',
        opacity,
      }}
    >
      <div
        style={{
          fontFamily: font,
          fontWeight: 900,
          fontSize: height * 0.055,
          color: '#fff',
          textAlign: 'center',
          maxWidth: '84%',
          lineHeight: 1.12,
          textShadow: '0 4px 24px rgba(0,0,0,0.55)',
        }}
      >
        {title}
      </div>
    </AbsoluteFill>
  );
};

const ProgressBar: React.FC<{color: string}> = ({color}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, height} = useVideoConfig();
  const pct = interpolate(frame, [0, durationInFrames - 1], [0, 100], {
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        bottom: 0,
        width: `${pct}%`,
        height: Math.max(4, height * 0.004),
        background: color,
      }}
    />
  );
};

export const Video: React.FC<VideoProps> = ({
  videoSrc,
  words,
  profile,
  title,
}) => {
  const {grade, captions, graphics} = profile;

  // The grade is applied here rather than baked in by ffmpeg so it stays
  // adjustable in the studio without re-running the cut.
  const filter = grade
    ? `saturate(${grade.saturation}) contrast(${grade.contrast})`
    : undefined;

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <AbsoluteFill style={{filter}}>
        <OffthreadVideo
          src={staticFile(videoSrc)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
        />
      </AbsoluteFill>

      {title && graphics.titleCard ? (
        <TitleCard
          title={title}
          seconds={graphics.titleCardSec}
          font={resolveFont(captions.font)}
        />
      ) : null}

      <Captions words={words} style={captions} />

      {graphics.progressBar ? (
        <ProgressBar color={graphics.progressBarColor} />
      ) : null}
    </AbsoluteFill>
  );
};
