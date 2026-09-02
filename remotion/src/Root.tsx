import React from 'react';
import {Composition} from 'remotion';
import {Video} from './Video';
import type {VideoProps} from './types';
import defaultProps from './default-props.json';

export const RemotionRoot: React.FC = () => {
  const props = defaultProps as unknown as VideoProps;
  return (
    <Composition
      id="Video"
      component={Video}
      // Every dimension comes from the style profile, so a reference shot in
      // 1080x1920 at 30fps reproduces at exactly that size.
      width={props.profile.format.width}
      height={props.profile.format.height}
      fps={props.profile.format.fps}
      durationInFrames={props.durationInFrames}
      defaultProps={props}
      calculateMetadata={({props: p}) => ({
        width: p.profile.format.width,
        height: p.profile.format.height,
        fps: p.profile.format.fps,
        durationInFrames: p.durationInFrames,
      })}
    />
  );
};
