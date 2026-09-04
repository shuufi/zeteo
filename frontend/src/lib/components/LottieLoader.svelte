<script lang="ts">
  import { onDestroy } from 'svelte';
  import { DotLottie } from '@lottiefiles/dotlottie-web';
  import loadingSrc from '../assets/loading.lottie?url';

  // Source animation composition is 800x200 (4:1) — sizing the canvas to
  // match keeps the artwork filling it, instead of a square canvas leaving
  // big transparent bands above/below.
  const ASPECT_RATIO = 200 / 800;

  let { size = 96 }: { size?: number } = $props();
  const height = $derived(Math.round(size * ASPECT_RATIO));

  let canvas: HTMLCanvasElement;
  let dotLottie: DotLottie | undefined;

  function mount(node: HTMLCanvasElement) {
    dotLottie = new DotLottie({
      canvas: node,
      src: loadingSrc,
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

<canvas bind:this={canvas} use:mount width={size} {height} class="block"></canvas>
