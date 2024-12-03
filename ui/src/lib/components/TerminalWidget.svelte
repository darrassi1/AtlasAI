<script>
  import { onMount, onDestroy } from "svelte";
  import { Terminal } from "@xterm/xterm";
  import { FitAddon } from "@xterm/addon-fit";
  import { agentState } from "$lib/store";
  import "@xterm/xterm/css/xterm.css";

  let fitAddon;
  let terminal;
  let isTerminalClear = true;
  let isTerminalPopupOpen = false;
  let handleResize;

  onMount(async () => {
    const terminalBg = getComputedStyle(document.body).getPropertyValue("--terminal-window-background");
    const terminalFg = getComputedStyle(document.body).getPropertyValue("--terminal-window-foreground");

    terminal = new Terminal({
      disableStdin: true,
      cursorBlink: true,
      convertEol: true,
      rows: 1,
      theme: {
        background: terminalBg,
        foreground: terminalFg,
        innerText: terminalFg,
        cursor: terminalFg,
        selectionForeground: terminalBg,
        selectionBackground: terminalFg,
      },
    });

    fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.open(document.getElementById("terminal-content"));
    fitAddon.fit();

    let previousState = {};

    agentState.subscribe((state) => {
      if (state && state.terminal_session) {
        let command = state.terminal_session.command || 'echo "Waiting..."';
        let output = state.terminal_session.output || "Waiting...";
        let title = state.terminal_session.title || "Terminal";

        if (command !== previousState.command || output !== previousState.output || title !== previousState.title) {
          if (title) {
            document.getElementById("terminal-title").innerText = title;
          }
          terminal.reset();
          terminal.write(`$ ${command}\r\n\r\n${output}\r\n`);
          terminal.scrollToBottom();
          previousState = { command, output, title };
          isTerminalClear = false;
        }
      } else {
        clearTerminal();
      }

      fitAddon.fit();
    });

    const handleResize = fitAddon.fit.bind(fitAddon);
    window.addEventListener('resize', handleResize);
  });

  onDestroy(() => {
    if (handleResize) {
      window.removeEventListener('resize', handleResize);
    }

  });

  function clearTerminal() {
    terminal.reset();
    document.getElementById("terminal-title").innerText = "Terminal";
    isTerminalClear = true;
  }

  function toggleTerminalPopup() {
    isTerminalPopupOpen = !isTerminalPopupOpen;
    if (isTerminalPopupOpen) {
      // Additional actions when opening the terminal popup (if any)

    //terminal.open(document.getElementById("terminal-popup-content"));
    //fitAddon.fit();
    } else {
      // Additional actions when closing the terminal popup (if any)

    }
  }
</script>

<div class="w-full h-full flex flex-col border-[3px] overflow-hidden rounded-xl border-window-outline">
  <div class="flex items-center justify-between p-2 border-b bg-terminal-window-ribbon">
    <div class="flex items-center ml-2 space-x-2">
   <!--
   <div class="w-3 h-3 bg-red-500 rounded-full animate-blink"></div>
      <div class="w-3 h-3 bg-blue-500 rounded-full animate-blink animation-delay-200"></div>
      <div class="w-3 h-3 bg-green-500 rounded-full animate-blink animation-delay-400"></div>-->

    </div>
    <span id="terminal-title" class="text-tertiary text-sm">Terminal</span>
    {#if !isTerminalClear}
    <button class="clear-button text-sm p-1 ml-auto bg-gray-300 rounded hover:bg-gray-400" on:click={clearTerminal}>Clear</button>
    {/if}
    <button class="popup-button text-sm p-1 ml-2 bg-gray-300 rounded hover:bg-gray-400" on:click={toggleTerminalPopup}>
      {isTerminalPopupOpen ? "✖" : "⛶"}
    </button>
  </div>
  <div class="relative w-full h-full">
    <div id="terminal-content" class="absolute inset-0 bg-terminal-window-background resizable"></div>
    {#if isTerminalPopupOpen}
    <div class="fixed top-0 left-0 right-0 bottom-0 flex justify-center items-center bg-black bg-opacity-50 z-50">
      <div class="bg-white p-4 rounded-lg shadow-lg">
        <!-- Additional controls or content for the terminal popup -->
        <div class="text-xl mb-2">Terminal View</div>
        <div id="terminal-popup-content" class="bg-terminal-window-background h-64"></div>
        <button class="clear-button text-sm p-1 bg-gray-300 rounded hover:bg-gray-400 mt-4" on:click={toggleTerminalPopup}>Close</button>
      </div>
    </div>
    {/if}
  </div>
</div>

<style>
  .animate-blink {
    animation: blink 1s ease-in-out infinite;
  }

  @keyframes blink {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0; transform: scale(0.8); }
    100% { opacity: 1; transform: scale(1); }
  }

  .clear-button {
    background-color: black;
    color: whitesmoke;
    transition: background-color 0.3s, color 0.3s;
  }

  .clear-button:hover {
    background-color: whitesmoke;
    color: black;
  }

  .popup-button {
    background-color: rgb(185, 185, 185);
    color: #000000;
    transition: background-color 0.3s, color 0.3s;
  }

  .popup-button:hover {
    background-color: whitesmoke;
    color: black;
  }

  /* Styling for resizable element */
  .resizable {
    resize: both;
    overflow: auto;
  }
</style>
