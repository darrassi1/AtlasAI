
<script>
  import { agentState, messages } from "$lib/store";
  import { afterUpdate, onMount } from "svelte";
  import { marked } from "marked";
  import DomPurify from "dompurify";
  import * as monaco from 'monaco-editor';

  let messageContainer;
  let showModal = false;
  let modalImage = '';
  let showFileList = false;
  let selectedFiles = [];
  let showDiffPopup = false;
  let oldFileContent = '';
  let newFileContent = '';
  let diffEditor;
  let selectedLines = { left: new Set(), right: new Set() };
  let lineCount = { left: 0, right: 0 };
  let isDarkMode = true;

  onMount(() => {
    const addCopyListeners = () => {
      document.querySelectorAll('.copy-btn:not([data-listener])').forEach((btn) => {
        btn.dataset.listener = 'true';
        btn.addEventListener('click', () => {
          const codeBlock = btn.closest('.relative');
          if (codeBlock) {
            const codeContent = codeBlock.textContent.replace(/Copy|Copied!/, '').trim();
            navigator.clipboard.writeText(codeContent)
              .then(() => {
                btn.textContent = 'Copied!';
                setTimeout(() => btn.textContent = 'Copy', 2000);
              })
              .catch(err => console.error('Failed to copy text: ', err));
          }
        });
      });
    };

    addCopyListeners();
    const observer = new MutationObserver(addCopyListeners);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => observer.disconnect();
  });

  afterUpdate(() => {
    if ($messages && $messages.length > 0) {
      messageContainer.scrollTo({
        top: messageContainer.scrollHeight,
        behavior: "smooth"
      });
    }
  });

  const openModal = (image) => {
    modalImage = image;
    showModal = true;
  };

  const closeModal = () => showModal = false;

  const downloadImage = (dataUrl) => {
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = 'image.png';
    link.click();
  };

  const formatMessage = (message) => {
    const msg = addCopyButtonsToCodeBlocks(message);
    const markdown = marked(msg);
    return DomPurify.sanitize(markdown);
  };

  const addCopyButtonsToCodeBlocks = (html) => {
    return html.replace(/```[\s\S]*?```/g, (codeBlock) =>
      `<div class="relative rounded-lg overflow-hidden my-4 bg-gray-800 border border-gray-700 text-white">
        <button class="copy-btn absolute top-2.5 right-2.5 bg-gray-700 text-white border-none px-2.5 py-1.25 text-xs cursor-pointer hover:bg-gray-600 transition-colors duration-200" title="Copy code">Copy</button>
        ${codeBlock}
      </div>`
    );
  };

  const detectFiles = (message) => {
    const fileRegex = /(?:^|\s|\/)([a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_-]+)*\.[a-zA-Z0-9]+)/g;
    return [...message.matchAll(fileRegex)].map(match => match[1]);
  };

  const toggleFileList = (message) => {
    selectedFiles = detectFiles(message);
    showFileList = !showFileList;
  };

  const openDiffPopup = (file) => {
    showDiffPopup = true;
    oldFileContent = "Old content of " + file;
    newFileContent = "New content of " + file;

    setTimeout(() => {
      diffEditor = monaco.editor.createDiffEditor(document.getElementById('diffContainer'), {
        language: getLanguageFromFileName(file),
        theme: isDarkMode ? 'vs-dark' : 'vs-light',
        automaticLayout: true,
        renderSideBySide: true,
        readOnly: false,
        lineNumbers: 'on',
        minimap: { enabled: true },
        diffWordWrap: 'on',
        scrollBeyondLastLine: false,
        renderIndicators: true,
        renderOverviewRuler: true,
      });

      const originalModel = monaco.editor.createModel(oldFileContent, getLanguageFromFileName(file));
      const modifiedModel = monaco.editor.createModel(newFileContent, getLanguageFromFileName(file));

      diffEditor.setModel({
        original: originalModel,
        modified: modifiedModel
      });

      lineCount.left = originalModel.getLineCount();
      lineCount.right = modifiedModel.getLineCount();

      const originalEditor = diffEditor.getOriginalEditor();
      const modifiedEditor = diffEditor.getModifiedEditor();

      [originalEditor, modifiedEditor].forEach((editor, index) => {
        const side = index === 0 ? 'left' : 'right';
        editor.onMouseDown((e) => {
          if (e.target.type === monaco.editor.MouseTargetType.GUTTER_LINE_NUMBERS) {
            const lineNumber = e.target.position.lineNumber;
            toggleLineSelection(side, lineNumber);
            updateLineDecorations(editor, side);
          }
        });

        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KEY_S, () => {
          const selection = editor.getSelection();
          if (selection) {
            for (let i = selection.startLineNumber; i <= selection.endLineNumber; i++) {
              toggleLineSelection(side, i);
            }
            updateLineDecorations(editor, side);
          }
        });
      });

      updateSelectionCounter();
    }, 0);
  };

  const getLanguageFromFileName = (fileName) => {
    const extension = fileName.split('.').pop().toLowerCase();
    const languageMap = {
      'js': 'javascript',
      'ts': 'typescript',
      'py': 'python',
      'html': 'html',
      'css': 'css',
      'json': 'json',
    };
    return languageMap[extension] || 'plaintext';
  };

  const toggleLineSelection = (side, lineNumber) => {
    if (selectedLines[side].has(lineNumber)) {
      selectedLines[side].delete(lineNumber);
    } else {
      selectedLines[side].add(lineNumber);
    }
    updateSelectionCounter();
  };

  const updateLineDecorations = (editor, side) => {
    editor.deltaDecorations([], Array.from(selectedLines[side]).map(line => ({
      range: new monaco.Range(line, 1, line, 1),
      options: {
        isWholeLine: true,
        className: side === 'left' ? 'bg-red-200 bg-opacity-30' : 'bg-green-200 bg-opacity-30',
        linesDecorationsClassName: side === 'left' ? 'before:content-["-"] before:text-red-500 before:mr-1' : 'before:content-["+"] before:text-green-500 before:mr-1'
      }
    })));
  };

  const updateSelectionCounter = () => {
    document.getElementById('selectionCounter').textContent =
      `Selected: ${selectedLines.left.size} (left) / ${selectedLines.right.size} (right)`;
  };

  const closeDiffPopup = () => {
    showDiffPopup = false;
    if (diffEditor) {
      diffEditor.dispose();
    }
    selectedLines = { left: new Set(), right: new Set() };
  };

  const saveChanges = () => {
    const modifiedModel = diffEditor.getModifiedEditor().getModel();
    const selectedChanges = Array.from(selectedLines.right)
      .map(line => modifiedModel.getLineContent(line))
      .join('\n');
    console.log("Saving changes:", selectedChanges);
    closeDiffPopup();
  };

  const revertChanges = () => {
    if (confirm('Are you sure you want to revert all changes?')) {
      diffEditor.getModifiedEditor().getModel().setValue(oldFileContent);
      selectedLines = { left: new Set(), right: new Set() };
      updateSelectionCounter();
      updateLineDecorations(diffEditor.getOriginalEditor(), 'left');
      updateLineDecorations(diffEditor.getModifiedEditor(), 'right');
    }
  };

  const revertSelectedChanges = () => {
    if (confirm('Are you sure you want to revert selected changes?')) {
      const originalModel = diffEditor.getOriginalEditor().getModel();
      const modifiedModel = diffEditor.getModifiedEditor().getModel();

      const revertedLines = Array.from(selectedLines.right).map(lineNumber => ({
        lineNumber,
        text: originalModel.getLineContent(lineNumber)
      }));

      modifiedModel.pushEditOperations([], revertedLines.map(line => ({
        range: new monaco.Range(line.lineNumber, 1, line.lineNumber, Number.MAX_VALUE),
        text: line.text
      })), () => null);

      selectedLines.right.clear();
      updateSelectionCounter();
      updateLineDecorations(diffEditor.getModifiedEditor(), 'right');
    }
  };

  const selectAll = (side) => {
    selectedLines[side] = new Set(Array.from({ length: lineCount[side] }, (_, i) => i + 1));
    updateLineDecorations(side === 'left' ? diffEditor.getOriginalEditor() : diffEditor.getModifiedEditor(), side);
    updateSelectionCounter();
  };

  const deselectAll = (side) => {
    selectedLines[side].clear();
    updateLineDecorations(side === 'left' ? diffEditor.getOriginalEditor() : diffEditor.getModifiedEditor(), side);
    updateSelectionCounter();
  };

  const toggleDarkMode = () => {
    isDarkMode = !isDarkMode;
    if (diffEditor) {
      monaco.editor.setTheme(isDarkMode ? 'vs-dark' : 'vs-light');
    }
  };
</script>

<div id="message-container" class="flex flex-col flex-1 gap-2 overflow-y-auto rounded-lg" bind:this={messageContainer}>
  {#if $messages !== null && $messages.length !== 0}
    <div class="flex flex-col divide-y-2">
      {#each $messages as message}
        <div class="flex items-start gap-2 px-2 py-4">
          <img src={message.from_devika ? "/assets/devika-avatar.png" : "/assets/user-avatar.svg"} alt={`${message.from_devika ? "Atlas" : "User"}'s Avatar`} class="flex-shrink-0 rounded-full avatar w-7 h-7" />
          <div class="flex flex-col w-full text-sm">
            <p class="text-xs text-gray-400">
              {message.from_devika ? "Atlas" : "You"}
              <span class="timestamp ml-2 text-gray-500">{new Date(message.timestamp).toLocaleTimeString()}</span>
            </p>
            {#if message.from_devika && message.message.startsWith("{")}
              <div class="flex flex-col w-full gap-5" contenteditable="false">
                {@html `<strong>Here's my step-by-step plan:</strong>`}
                <div class="flex flex-col gap-3">
                {#if JSON.parse(message.message)}
                  {#each Object.entries(JSON.parse(message.message)) as [step, description]}
                    <div class="flex items-center gap-2">
                      <input type="checkbox" id="step-{step}" disabled />
                      <label for="step-{step}" class="cursor-auto"><strong>Step {step}</strong>: {description}</label>
                    </div>
                  {/each}
                {/if}
                </div>
              </div>
            {:else if /https?:\/\/[^\s]+/.test(message.message)}
              <div class="w-full cursor-auto" contenteditable="false">
                {@html message.message.replace(
                  /(https?:\/\/[^\s]+)/g,
                  '<u><a href="$1" target="_blank" style="font-weight: bold;">$1</a></u>'
                )}
              </div>
            {:else if message.message.startsWith('data:image/png;base64,')}
              <div class="w-full cursor-auto" contenteditable="false">
                <div class="image-container">
                  <img src="{message.message}" alt="" />
                  <button class="preview-btn" on:click={() => openModal(message.message)}>Preview</button>
                  <button class="download-btn" on:click={() => downloadImage(message.message)}>Download</button>
                </div>
              </div>
            {:else}
              <div class="w-full" contenteditable="false">{@html formatMessage(message.message)}</div>
            {/if}
          </div>
          {#if detectFiles(message.message).length > 0}
            <button class="file-list-btn bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded transition-colors duration-200" on:click={() => toggleFileList(message.message)} title="View detected files">
              Files
            </button>
          {/if}
        </div>
      {/each}
    </div>
    {#if $agentState !== null && !$agentState.agent_is_active}
      <div class="flex justify-center w-full mt-0.5">
        <button class="bg-black hover:bg-blue-900 text-white dark:bg-white dark:hover:bg-gray-200 dark:text-blue-600 font-semibold py-0 px-0 rounded-md shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-white focus:ring-opacity-50 transition-all duration-300 ease-in-out w-32">
          <span class="mr-2">👉</span>Continue
        </button>
      </div>
    {/if}
  {/if}
</div>

{#if showModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={closeModal}>
    <div class="bg-white dark:bg-gray-800 p-4 rounded-lg max-w-3xl max-h-[90vh] overflow-auto" on:click|stopPropagation>
      <button class="absolute top-2 right-2 text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-100" on:click={closeModal}>&times;</button>
      <img src={modalImage} alt="" class="max-w-full h-auto" />
    </div>
  </div>
{/if}

{#if showFileList}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-md w-full">
      <h2 class="text-xl font-bold mb-4 dark:text-white">Detected Files</h2>
      <ul class="space-y-2">
        {#each selectedFiles as file}
          <li>
            <button class="w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded transition-colors duration-200 dark:text-white" on:click={() => openDiffPopup(file)}>{file}</button>
          </li>
        {/each}
      </ul>
      <button class="mt-4 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white font-bold py-2 px-4 rounded transition-colors duration-200" on:click={() => showFileList = false}>Close</button>
    </div>
  </div>
{/if}

{#if showDiffPopup}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg w-11/12 h-5/6 flex flex-col">
      <h2 class="text-xl font-bold mb-4 dark:text-white">File Diff</h2>
      <div class="flex justify-between mb-2">
        <div>
          <button class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-1 px-2 rounded text-sm mr-2 transition-colors duration-200" on:click={() => selectAll('left')} title="Select all lines on the left side">Select All (Left)</button>
          <button class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-1 px-2 rounded text-sm transition-colors duration-200" on:click={() => deselectAll('left')} title="Deselect all lines on the left side">Deselect All (Left)</button>
        </div>
        <div>
          <button class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-1 px-2 rounded text-sm mr-2 transition-colors duration-200" on:click={() => selectAll('right')} title="Select all lines on the right side">Select All (Right)</button>
          <button class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-1 px-2 rounded text-sm transition-colors duration-200" on:click={() => deselectAll('right')} title="Deselect all lines on the right side">Deselect All (Right)</button>
        </div>
      </div>
      <div id="selectionCounter" class="mb-2 text-sm font-semibold dark:text-white">Selected: 0 (left) / 0 (right)</div>
      <div id="diffContainer" class="flex-grow"></div>
      <div class="flex justify-between space-x-4 mt-4">
        <button class="bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white font-bold py-2 px-4 rounded transition-colors duration-200" on:click={toggleDarkMode} title="Toggle dark/light mode">
          {isDarkMode ? 'Light Mode' : 'Dark Mode'}
        </button>
        <div>
          <button class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded transition-colors duration-200 mr-2" on:click={revertChanges} title="Revert all changes">Revert All</button>
          <button class="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-2 px-4 rounded transition-colors duration-200 mr-2" on:click={revertSelectedChanges} title="Revert selected changes">Revert Selected</button>
          <button class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded transition-colors duration-200 mr-2" on:click={saveChanges} title="Save all changes">Save Changes</button>
          <button class="bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white font-bold py-2 px-4 rounded transition-colors duration-200" on:click={closeDiffPopup} title="Close diff viewer">Close</button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  #diffContainer {
    height: 100%;
  }

  :global(.monaco-editor .margin-view-overlays .line-numbers) {
    cursor: pointer;
  }

  :global(.monaco-editor .selected-text) {
    background-color: rgba(173, 214, 255, 0.3);
  }

  :global(.monaco-diff-editor .diff-review-line-number) {
    text-align: right;
    padding-right: 10px;
  }

  :global(.monaco-editor .line-numbers) {
    cursor: pointer;
  }

  :global(.monaco-editor .line-numbers::before) {
    content: attr(data-line-number);
    position: absolute;
    right: 100%;
    padding-right: 5px;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .file-list-btn, .copy-btn {
    animation: fadeIn 0.3s ease-in-out;
  }

  @media (prefers-reduced-motion: reduce) {
    .file-list-btn, .copy-btn {
      animation: none;
    }
  }
</style>
