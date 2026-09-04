<script lang="ts">
  import { onDestroy } from 'svelte';
  import { DotLottie } from '@lottiefiles/dotlottie-web';
  import loadingSrc from '../assets/loading.lottie?url';

  let {
    src = loadingSrc,
    size = 96,
    // Default matches loading.lottie's 800x200 (4:1) composition — pass a
    // different ratio (e.g. 1 for a square animation) for other sources.
    aspectRatio = 200 / 800,
    // When true, canvas visually fills its parent's width (CSS) instead of
    // rendering at `size` px — use with a sized wrapper (e.g. class="w-1/2").
    responsive = false,
  }: { src?: string; size?: number; aspectRatio?: number; responsive?: boolean } = $props();
  const height = $derived(Math.round(size * aspectRatio));

  let canvas: HTMLCanvasElement;
  let dotLottie: DotLottie | undefined;

  function mount(node: HTMLCanvasElement) {
    dotLottie = new DotLottie({
      canvas: node,
      src,
      loop: true,
      autoplay: true,
    });
    return {
      destroy() {
        dotLottie?.destroy();
      },
    };
  }

  onDestroy(() => dotLottie?.destroy());
</script>

<canvas
  bind:this={canvas}
  use:mount
  width={size}
  {height}
  class="block {responsive ? 'w-full h-auto' : ''}"
></canvas>
