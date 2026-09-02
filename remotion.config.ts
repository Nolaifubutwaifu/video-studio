import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// The public/ folder is where tools/render.py stages the trimmed take.
Config.setPublicDir('public');
