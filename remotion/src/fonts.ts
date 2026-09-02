/**
 * Font registry.
 *
 * The style profile names a font as a plain string, but Remotion needs each
 * Google font imported statically so it can be bundled and preloaded before
 * the first frame is drawn. A curated map covers the faces that actually show
 * up in vertical social captions; anything unrecognised falls back to a system
 * stack rather than failing the render.
 */
import {loadFont as loadAnton} from '@remotion/google-fonts/Anton';
import {loadFont as loadBebas} from '@remotion/google-fonts/BebasNeue';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadMontserrat} from '@remotion/google-fonts/Montserrat';
import {loadFont as loadPoppins} from '@remotion/google-fonts/Poppins';

type Loader = () => {fontFamily: string};

const REGISTRY: Record<string, Loader> = {
  anton: loadAnton as Loader,
  bebasneue: loadBebas as Loader,
  'bebas neue': loadBebas as Loader,
  inter: loadInter as Loader,
  montserrat: loadMontserrat as Loader,
  poppins: loadPoppins as Loader,
};

const SYSTEM_STACK =
  '-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif';

const cache = new Map<string, string>();

export const resolveFont = (name: string | undefined): string => {
  if (!name) return SYSTEM_STACK;
  const key = name.trim().toLowerCase();
  if (cache.has(key)) return cache.get(key) as string;

  const loader = REGISTRY[key];
  if (!loader) {
    // Not a bundled Google font: pass the name through and let it resolve
    // locally if the machine happens to have it, with a real fallback behind.
    const stack = `"${name}", ${SYSTEM_STACK}`;
    cache.set(key, stack);
    return stack;
  }

  const {fontFamily} = loader();
  cache.set(key, fontFamily);
  return fontFamily;
};

export const AVAILABLE_FONTS = Object.keys(REGISTRY);
