import { mount } from 'svelte'
import '@tailwindplus/elements'
import '@fontsource-variable/inter'
import './styles/global.css'
import App from './App.svelte'

const app = mount(App, {
  target: document.getElementById('app')!,
})

export default app
