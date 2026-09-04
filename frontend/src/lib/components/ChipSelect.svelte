<script lang="ts" generics="T extends string">
  let {
    id,
    prefix = '',
    options,
    labels,
    selected = $bindable(options[0]),
  }: { id: string; prefix?: string; options: T[]; labels?: string[]; selected?: T } = $props();

  // Selecting an option always fires a native bubbling change event on the
  // host (@tailwindplus/elements) — bind:selected only actually stays live
  // where a caller listens for it; callers that just pass a static value
  // (see docs/adr/0005) see no different behaviour than before.
  function handleChange(e: Event): void {
    selected = (e.currentTarget as HTMLElement & { value: string }).value as T;
  }

  // Optional display label parallel to `options`, for when the bound value
  // (e.g. a lowercase enum code) shouldn't be shown to the user verbatim.
  function labelFor(option: T): string {
    const index = options.indexOf(option);
    return labels && index >= 0 ? labels[index] : option;
  }
</script>

<div class="flex items-center gap-1.5">
  {#if prefix}<span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">{prefix}</span>{/if}

  <el-select {id} name={id} value={selected} onchange={handleChange} class="inline-block">
    <button
      type="button"
      class="grid min-w-36 cursor-default grid-cols-1 rounded-md bg-white py-1.5 pr-2 pl-3 text-left text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-600 sm:text-sm/6 dark:bg-white/5 dark:text-white dark:outline-white/10 dark:focus-visible:outline-indigo-500"
    >
      <el-selectedcontent class="col-start-1 row-start-1 truncate pr-6">{labelFor(selected)}</el-selectedcontent>
      <svg
        viewBox="0 0 16 16"
        fill="currentColor"
        data-slot="icon"
        aria-hidden="true"
        class="col-start-1 row-start-1 size-5 self-center justify-self-end text-gray-500 sm:size-4 dark:text-gray-400"
      >
        <path
          fill-rule="evenodd"
          d="M5.22 10.22a.75.75 0 0 1 1.06 0L8 11.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-2.25 2.25a.75.75 0 0 1-1.06 0l-2.25-2.25a.75.75 0 0 1 0-1.06ZM10.78 5.78a.75.75 0 0 1-1.06 0L8 4.06 6.28 5.78a.75.75 0 0 1-1.06-1.06l2.25-2.25a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06Z"
          clip-rule="evenodd"
        />
      </svg>
    </button>

    <el-options
      anchor="bottom start"
      popover
      class="max-h-60 w-(--button-width) overflow-auto rounded-md bg-white py-1 text-base shadow-lg outline-1 outline-black/5 [--anchor-gap:--spacing(1)] data-leave:transition data-leave:transition-discrete data-leave:duration-100 data-leave:ease-in data-closed:data-leave:opacity-0 sm:text-sm dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
    >
      {#each options as option (option)}
        <el-option
          value={option}
          class="group/option relative block cursor-default py-2 pr-4 pl-8 text-gray-900 select-none focus:bg-indigo-600 focus:text-white focus:outline-hidden dark:text-white dark:focus:bg-indigo-500"
        >
          <span class="block truncate font-normal group-aria-selected/option:font-semibold">{labelFor(option)}</span>
          <span
            class="absolute inset-y-0 left-0 flex items-center pl-1.5 text-indigo-600 group-not-aria-selected/option:hidden group-focus/option:text-white in-[el-selectedcontent]:hidden dark:text-indigo-400"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" data-slot="icon" aria-hidden="true" class="size-5">
              <path
                fill-rule="evenodd"
                d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                clip-rule="evenodd"
              />
            </svg>
          </span>
        </el-option>
      {/each}
    </el-options>
  </el-select>
</div>
