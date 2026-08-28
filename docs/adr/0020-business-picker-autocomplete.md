# Business picker rebuilt on a generic `Autocomplete` component (`el-autocomplete`)

`0019` rebuilt `BusinessPicker` on `el-select`/`el-option`. This ADR replaces that with `el-autocomplete`/`el-option` instead, since a type-to-filter search field reads better than a dropdown list once the BU/company list grows, and matches the Tailwind Plus "Autocomplete" pattern rather than "Select".

The reusable chrome (label, input, search-icon button, `el-options` popover) is extracted into `Autocomplete.svelte` — a generic component that takes only `id`/`label`/`placeholder`/`defaultValue` and a `children` snippet for the option list. Callers render their own `<el-option>` markup into that snippet, so the component isn't coupled to any one data shape (flat list, grouped list, disabled headers, etc. are all just markup the caller controls). `BusinessPicker` is the first consumer: it flattens `businessUnits` into BU rows (bold, selectable — picking one selects the whole BU) followed by indented company rows, all filterable by `el-autocomplete`'s built-in substring match against each option's `value`/text.

Each option's `value` attribute is set to its display label directly (`bu.label` / `company.name`) rather than a composite code, since `el-autocomplete` writes the selected option's `value` straight into the input on pick — using the human-readable label there keeps the input text clean. This is safe because selection remains decorative per `0005`/`0015`: nothing downstream reads the picked value, only the chip's own displayed text changes.

Period and vs Budget (`ChipSelect`, from `0019`) are unaffected — they stay on `el-select`, since a short fixed option list suits a dropdown better than a search field.

**Status**: supersedes `0019`'s choice of `el-select` for the Business chip specifically.
