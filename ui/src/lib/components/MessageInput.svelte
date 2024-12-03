<script>
  import { socket, fetchProjectFiles } from "$lib/api";
  import { agentState, messages } from "$lib/store";
  import { calculateTokens } from "$lib/token";
  import { Icons } from "../icons";
  import { storeSelectedProject } from "../store.js";
  import { toast } from "svelte-sonner";
  import { onDestroy, onMount } from "svelte";

  let currentPid = null;
  let files1 = [];
  let selectedFiles = [];
  let showFileSelection = false;
  let incdevActive = false;
  let showRewritePopup = false;
  let selectedOption = '';
  let originalText = '';
  let refinedText = '';
  let isRewriting = false;
  let messageInput = "";
  let recognition = null;
  let isSpeechRecognitionActive = false;
  let isAgentActive = false;

  const suggestions = ["bugs", "feature", "run", "answer"];
  let cursorPosition = { top: 0, left: 0 };

  $: if ($storeSelectedProject && $agentState !== null) {
    isAgentActive = $agentState.agent_is_active;
  } else {
    isAgentActive = false;
  }

  onMount(() => {
    setupSocketListeners();
    setupSSE();
  });

  onDestroy(() => {
    removeSocketListeners();
  });

  function setupSocketListeners() {
    socket.on('pid', handlePid);
    socket.on('pidkilled', handlePidKilled);
    socket.on('kill_process_response', handleKillProcessResponse);
  }

  function removeSocketListeners() {
    if (socket.connected) {
      socket.off("pid");
      socket.off("kill_process_response");
      socket.off("pidkilled");
    }
  }

  function setupSSE() {
    const eventSource = new EventSource('/api/llm-stream');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updateTextarea(data.text);
    };
    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      eventSource.close();
    };
  }

  function handlePid(data) {
    console.log('Process started with PID:', data.pid);
    console.log('command:', data.command);
    currentPid = data.pid;
    toast.info(`Process started with PID: ${data.pid}`, { duration: 3000 });
  }

  function handlePidKilled(data) {
    console.log('killing PID:', data.pid);
    console.log('command:', data.command);
    if (currentPid === data.pid) {
      currentPid = null;
    }
    toast.info(`killed: ${data.pid}`, { duration: 3000 });
  }

  function handleKillProcessResponse(data) {
    console.log(data.status);
    console.log(data.message);
    toast.info(data.message, { duration: 3000 });
  }

  function killProcess() {
    if (currentPid) {
      socket.emit('kill_process', { pid: currentPid });
    } else {
      console.log('No process to kill.');
      toast.info('No process to kill.', { duration: 500 });
    }
  }

  function handleInput(event) {
    const inputText = event.target.value;
    const lastChar = inputText.slice(-1);
    const { top, left } = getCursorPosition(event.target);
    cursorPosition = { top, left };
    lastChar === "/" ? renderSuggestions() : clearSuggestions();
  }

  function handleRewrite() {
    showRewritePopup = true;
    originalText = document.getElementById("message-input").value;
  }

  function selectOption(option) {
    selectedOption = option;
    refinedText = `Refined ${option}: ${originalText}`;
  }

  function applyRefinement() {
    updateTextarea(refinedText);
    showRewritePopup = false;
  }

  function renderSuggestions() {
    const suggestionsContainer = document.getElementById("suggestions-container");
    suggestionsContainer.innerHTML = "";
    const suggestionStyles = `
      .suggestion {
        padding: 0.01rem;
        cursor: pointer;
      }
      .suggestion:hover {
        background-color: red;
      }
    `;
    const styleSheet = document.createElement("style");
    styleSheet.type = "text/css";
    styleSheet.innerText = suggestionStyles;
    document.head.appendChild(styleSheet);

    suggestions.forEach((suggestion) => {
      const suggestionElement = document.createElement("div");
      suggestionElement.textContent = suggestion;
      suggestionElement.classList.add("suggestion");
      suggestionElement.style.position = "relative";
      suggestionElement.style.top = `${cursorPosition.top}px`;
      suggestionElement.style.left = `${cursorPosition.left}px`;
      suggestionElement.addEventListener("click", () => selectSuggestion(suggestion));
      suggestionsContainer.appendChild(suggestionElement);
    });
  }

  function clearSuggestions() {
    document.getElementById("suggestions-container").innerHTML = "";
  }

  function selectSuggestion(suggestion) {
    const inputTextArea = document.getElementById("message-input");
    const textBeforeCursor = inputTextArea.value.slice(0, inputTextArea.selectionStart);
    const textAfterCursor = inputTextArea.value.slice(inputTextArea.selectionEnd);
    inputTextArea.value = textBeforeCursor + suggestion + textAfterCursor;
    clearSuggestions();
  }

  async function toggleFileSelectionDropdown() {
    showFileSelection = !showFileSelection;
    if (showFileSelection && files1.length === 0) {
      files1 = await fetchProjectFiles();
    }
  }

  function toggleIncdev() {
    incdevActive = !incdevActive;
  }

  storeSelectedProject.subscribe((value) => {
    if (value) {
      files1 = [];
      selectedFiles = [];
    }
  });

  function initializeRecognition() {
    recognition = new window.webkitSpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.onresult = function(event) {
      messageInput = event.results[0][0].transcript;
      handleSendMessage();
    };
    recognition.onerror = function(event) {
      console.error('Speech recognition error:', event.error);
    };
    recognition.onend = function() {
      isSpeechRecognitionActive = false;
    };
  }

  function toggleSpeechRecognition() {
    if (!recognition) {
      initializeRecognition();
    }
    if (isSpeechRecognitionActive) {
      recognition.stop();
      isSpeechRecognitionActive = false;
    } else {
      recognition.start();
      isSpeechRecognitionActive = true;
    }
  }

  function toggleFileSelection(file) {
    selectedFiles = selectedFiles.includes(file)
      ? selectedFiles.filter(f => f !== file)
      : [...selectedFiles, file];
  }

  async function handleSendMessage() {
    const projectName = localStorage.getItem("selectedProject");
    const selectedModel = localStorage.getItem("selectedModel");
    const searchEngine = localStorage.getItem("selectedSearchEngine");

    if (!projectName) {
      alert("Please select a project first!");
      return;
    }
    if (!selectedModel) {
      alert("Please select a model first!");
      return;
    }

    const messageInput = document.getElementById("message-input").value.trim();
    if (messageInput !== "" && !isAgentActive) {
      const action = determineAction(messageInput);
      socket.emit("user-message", {
        action,
        message: messageInput,
        base_model: selectedModel,
        project_name: projectName,
        search_engine: searchEngine,
        selected_files: selectedFiles
      });
      document.getElementById("message-input").value = "";
    }
  }

  function determineAction(message) {
    const lowerMessage = message.toLowerCase();
    if ($messages.length === 0 && (lowerMessage.includes('github') || lowerMessage.includes('git'))) {
      return "continue1";
    } else if ($messages.length === 0 || lowerMessage.startsWith('create')) {
      return "execute_agent";
    } else if (lowerMessage.includes('/chemistry')) {
      return "execute_chemistry";
    } else if (lowerMessage.includes('/logo')) {
      return "execute_logo";
    } else if (selectedFiles.length > 0 && !lowerMessage.includes('/bugs')) {
      return "incdev";
    } else if (selectedFiles.length > 0 && lowerMessage.includes('/bugs')) {
      return "debugselectedfile";
    } else {
      return "continue";
    }
  }

  function setTokenSize(event) {
    const prompt = event.target.value;
    let tokens = calculateTokens(prompt);
    document.querySelector(".token-count").textContent = `${tokens}`;
  }

  function getCursorPosition(element) {
    const { selectionStart } = element;
    const div = document.createElement("div");
    document.body.appendChild(div);
    const styles = window.getComputedStyle(element);
    for (let prop of styles) {
      div.style[prop] = styles[prop];
    }
    div.style.position = 'absolute';
    div.style.visibility = 'hidden';
    div.style.whiteSpace = 'pre-wrap';
    div.textContent = element.value.substring(0, selectionStart);
    const span = document.createElement("span");
    span.textContent = element.value.substring(selectionStart);
    div.appendChild(span);
    const { offsetTop: top, offsetLeft: left } = span;
    document.body.removeChild(div);
    return { top, left };
  }

  async function processRewrite() {
    isRewriting = true;
    const textarea = document.getElementById("message-input");
    const content = textarea.value;

    try {
      const response = await fetch('/api/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, option: selectedOption })
      });

      if (!response.ok) throw new Error('Rewrite request failed');

      const reader = response.body.getReader();
      let accumulatedText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulatedText += new TextDecoder().decode(value);
        updateTextarea(accumulatedText);
      }
    } catch (error) {
      console.error('Rewrite error:', error);
      toast.error('Failed to rewrite text. Please try again.');
    } finally {
      isRewriting = false;
      showRewritePopup = false;
    }
  }

  function updateTextarea(text) {
    const textarea = document.getElementById("message-input");
    textarea.value = text;
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }
</script>

<div class="expandable-input relative">
  <button class="absolute text-secondary bg-primary p-1 right-4 bottom-40 rounded-full" on:click={killProcess}>Kill Process</button>

  <div class="py-3 px-1 rounded-md text-xs">
    Agent status:
    {#if $agentState !== null}
      {#if $agentState.agent_is_active}
        <span class="text-green-500">Active</span>
      {:else}
        <span class="text-orange-600">Inactive</span>
      {/if}
    {:else}
      Deactive
    {/if}

    <button
      class="absolute right-0 top-0 m-3 p-2 text-black-500 rounded hover:bg-gray-100"
      on:click={toggleSpeechRecognition}
    >
      <i class="fas fa-microphone{isSpeechRecognitionActive ? '' : '-slash'}"></i>
    </button>
    <div><label class="switch">
      <input type="checkbox" on:change={toggleIncdev} />
      <span class="slider round">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;IncrementalDev</span>
    </label></div>

    {#if !incdevActive}
      <button
        class="absolute right-10 top-0 m-3 p-1 text-black-500 rounded bg-gray-300 hover:bg-gray-100"
        on:click={toggleFileSelectionDropdown}
      >
        Select Context Files
      </button>
    {/if}

    <div class={`file-selection ${showFileSelection ? 'visible' : ''}`}>
      <h3>Select Files</h3>
      {#each files1 as file}
        <div>
          <input type="checkbox" id={file} on:change={() => toggleFileSelection(file.file)} />
          <label for={file.file}>{file.file}</label>
        </div>
      {/each}
    </div>
  </div>

  <div class="textarea-container">
    <div id="suggestions-container" class="suggestions"></div>
    <textarea
      id="message-input"
      class="w-full p-4 font-medium focus:text-foreground rounded-xl outline-none h-28 pr-20 bg-secondary"
      placeholder="Type your message...   or Type /  to Manually select an Agent"
      contenteditable="true"
      bind:value={messageInput}
      on:input={handleInput}
      on:keydown={(e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          handleSendMessage();
        }
      }}
      on:input={setTokenSize}
    ></textarea>
  </div>

  <button
    on:click={handleRewrite}
    class="absolute text-secondary bg-primary p-1.5 right-4 bottom-12 rounded-full z-10"
    class:animate-pulse={isRewriting}
  >
    {@html Icons.Rewrite}
  </button>

  <button
    on:click={handleSendMessage}
    class="absolute text-secondary bg-primary p-2 right-4 bottom-3 rounded-full"
  >
    {@html Icons.CornerDownLeft}
  </button>

  <p class="absolute text-tertiary p-2 right-4 top-11">
    <span class="token-count">0</span>
  </p>
</div>

{#if showRewritePopup}
  <div class="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50">
    <div class="bg-white bg-opacity-20 backdrop-filter backdrop-blur-lg p-6 rounded-xl shadow-xl w-11/12 max-w-4xl transform transition-all duration-300 ease-in-out">
      <h2 class="text-2xl font-bold mb-4 text-white">Linguistic Alchemy Lab</h2>
      <div class="grid grid-cols-2 gap-4 mb-4">
        <div class="space-y-2">
          <button class="w-full py-2 px-4 bg-blue-500 bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition duration-200 transform hover:scale-105" on:click={() => selectOption('Linguistic Alchemy')}>Linguistic Alchemy</button>
          <button class="w-full py-2 px-4 bg-purple-500 bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition duration-200 transform hover:scale-105" on:click={() => selectOption('Prompt Sculpting')}>Prompt Sculpting</button>
          <button class="w-full py-2 px-4 bg-green-500 bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition duration-200 transform hover:scale-105" on:click={() => selectOption('Syntax Harmonizer')}>Syntax Harmonizer</button>
          <button class="w-full py-2 px-4 bg-yellow-500 bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition duration-200 transform hover:scale-105" on:click={() => selectOption('Idea Amplifier')}>Idea Amplifier</button>
        </div>
        <div class="bg-white bg-opacity-10 p-4 rounded-lg">
          <h3 class="text-lg font-semibold mb-2 text-white">Refinement Preview</h3>
          <div class="grid grid-cols-2 gap-2 h-40 overflow-auto">
            <div class="text-sm text-white">{originalText}</div>
            <div class="text-sm text-green-300">{refinedText}</div>
          </div>
        </div>
      </div>
      <div class="flex justify-end space-x-4">
        <button class="py-2 px-4 bg-gray-500 bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition duration-200" on:click={() => showRewritePopup = false}>Cancel</button>
        <button class="py-2 px-4 bg-green-500 bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition duration-200" on:click={applyRefinement}>Apply Refinement</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .expandable-input textarea {
    min-height: 60px;
    max-height: 200px;
    resize: none;
  }

  .file-selection {
    position: absolute;
    right: 0;
    bottom: 10rem;
    background: #9aa3a8;
    color: #0e3556;
    border: 1px solid #ccc;
    border-radius: 0.5rem;
    padding: 1rem;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    display: none;
    max-height: 200px;
    overflow-y: auto;
  }

  .file-selection.visible {
    display: block;
  }

  .file-selection h3 {
    margin-bottom: 0.5rem;
  }

  .file-selection div {
    margin-bottom: 0.5rem;
  }

  .file-selection input[type="checkbox"] {
    margin-right: 0.5rem;
  }

  .suggestions {
    position: absolute;
  }

  .switch {
    position: absolute;
    display: inline-block;
    width: 40px;
    height: 24px;
    top: 16%;
    right: 220px;
    transform: translateY(-50%);
    margin-right: 48px;
  }

  .switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    transition: 0.4s;
    border-radius: 24px;
  }

  .slider:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 4px;
    bottom: 4px;
    background-color: white;
    transition: 0.4s;
    border-radius: 80%;
  }

  input:checked + .slider {
    background-color: #2196F3;
  }

  input:checked + .slider:before {
    transform: translateX(16px);
  }

  .slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    -webkit-transition: 0.4s;
    transition: 0.4s;
    border-radius: 34px;
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: .5;
    }
  }

  .animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  @keyframes orbitFloat {
    0% { transform: translateY(0px) rotate(2deg); }
    50% { transform: translateY(2px) rotate(0deg); }
    100% { transform: translateY(0px) rotate(2deg); }
  }

  .expandable-input button:hover {
    animation: orbitFloat 2s ease-in-out infinite;
  }

  button, input[type="checkbox"] {
    transition: all 0.3s ease;
  }

  button:focus-visible, input:focus-visible {
    outline: 2px solid #ffffff;
    outline-offset: 2px;
  }

  @keyframes audioPulse {
    0% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(255, 255, 255, 0); }
    100% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }
  }

  button:active {
    animation: audioPulse 0.2s cubic-bezier(0, 0, 0.2, 1);
  }
</style>
