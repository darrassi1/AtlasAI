<script>
  import { onDestroy, onMount } from 'svelte';
  import {
    initializeMonaco,
    sidebar,
    initializeEditorRef,
    disposeSidebar,
    disposeTabContainer,
    createModel,
    disposeEditor,
    enableTabSwitching,
    initializeRectifyFeature,
    deregisterCompletionProviders
  } from './MonacoEditor';
  import { socket, fetchProjectFiles } from "$lib/api";
  import { storeSelectedProject } from "$lib/store";
  import { agentState } from "../store.js";

  let isAgentActive = false;

  if ($agentState !== null) {
    isAgentActive = $agentState.agent_is_active;
  }

  let monaco;
  let models = {};
  let editor;
  let editorContainer;
  let tabContainer;
  let sidebarContainer;
  let autocompletionEnabled = true; // State variable for autocompletion mode

  const toggleAutocompletion = async () => {
    autocompletionEnabled = !autocompletionEnabled;
    await reCreateEditor(await fetchProjectFiles()); // Reinitialize editor to apply new autocompletion setting

  };




  const reCreateEditor = async (files) => {
    disposeEditor(editor);
    if (sidebarContainer) disposeSidebar(sidebarContainer);
    if (tabContainer) disposeTabContainer(tabContainer);
    models = {};
    editor = await initializeEditorRef(monaco, editorContainer);
    initializeRectifyFeature(editor)
    const projectName = localStorage.getItem("selectedProject");  // Get the project name
    let lastModel = null;

    files.forEach((file) => {
      // Check if the file is already rendered
      const model = createModel(monaco, file, projectName, editor, autocompletionEnabled); // Pass editor as a parameter

      models = {
        ...models,
        [file.file]: model
      };
          // Keep track of the last model
    lastModel = model;
            // Set the editor model to the current file's model
      editor.setModel(model);
    });

    enableTabSwitching(editor, models, tabContainer);
    sidebar(editor, models, sidebarContainer);
    await initializeEditor();
      // Explicitly set the editor's model to the last model after all tabs are created
  if (lastModel) {
    editor.setModel(lastModel);
  }

  };

  const patchOrFeature = async (files) => {
    disposeEditor(editor);
    if (sidebarContainer) disposeSidebar(sidebarContainer);
    if (tabContainer) disposeTabContainer(tabContainer);

    const projectName = localStorage.getItem("selectedProject");  // Get the project name
    let lastModel = null;

    files.forEach((file) => {
      // Check if the file is already rendered
      let model = models[file.file];
      if (model) {
        model.setValue(file.code);
      } else {
        model = createModel(monaco, file, projectName, editor, autocompletionEnabled);  // Pass editor as a parameter
        models = {
          ...models,
          [file.file]: model
        };
      }

                // Keep track of the last model
    lastModel = model;
            // Set the editor model to the current file's model
      editor.setModel(model);
    });

    enableTabSwitching(editor, models, tabContainer);
    sidebar(editor, models, sidebarContainer);
    await initializeEditor();
      if (lastModel) {
    editor.setModel(lastModel);
  }
  };

  let isInitializing = false;

  const initializeEditor = async () => {
    if (isInitializing) return;
    isInitializing = true;
    monaco = await initializeMonaco();
    const files = await fetchProjectFiles();
    await reCreateEditor(files);
    isInitializing = false;
  };

  onMount(async () => {
    await initializeEditor()
    socket.on('code', async function (data) {
      if(data.from === 'coder'){
        reCreateEditor(data.files);
      } else if (data.from === 'feature' || data.from === 'patcher') {
        patchOrFeature(data.files);
      }
    });
  });

  onDestroy(() => {
    disposeEditor(editor);
    models = {};
    deregisterCompletionProviders();
  });

  storeSelectedProject.subscribe((value) => {
    if (value) {
      initializeEditor()
    }
  });
</script>

<div class="w-full h-full flex flex-1 flex-col border-[3px] overflow-hidden rounded-xl border-window-outline p-0">
  <div class="flex items-center p-2 border-b bg-terminal-window-ribbon">
    <div class="flex ml-2 mr-4 space-x-2">
      <!--
<div class="w-3 h-3 bg-red-500 rounded-full animate-blink"></div>
      <div class="w-3 h-3 bg-blue-500 rounded-full animate-blink animation-delay-200"></div>
      <div class="w-3 h-3 bg-green-500 rounded-full animate-blink animation-delay-400"></div>-->
    </div>
    <div id="tabContainer"  class="flex text-tertiary text-sm overflow-x-auto" bind:this={tabContainer}></div>
    <button class="toggle-button {autocompletionEnabled ? '' : 'off'}" on:click={toggleAutocompletion}>
      {autocompletionEnabled ? 'Disable' : 'Enable'} Autocompletion
    </button>
    {#if Object.keys(models).length === 0}
      <div class="flex items-center text-tertiary text-sm">Code viewer&nbsp;&nbsp;</div>
      <div class="flex items-center text-tertiary text-sm">
        {#if $agentState !== null}
          {#if $agentState.agent_is_active}
          {:else}
            <button class="bg-orange-500 hover:bg-orange-600 text-white font-bold py-1 px-2 rounded focus:outline-none focus:shadow-outline" on:click={async () => await initializeEditor()}>
              Inactive
            </button>
          {/if}
        {:else}
        {/if}
      </div>
    {/if}
  </div>
  <div class="h-full w-full flex">
<button class="bg-green-500 hover:bg-orange-600 text-white font-bold py-1 px-2 rounded focus:outline-none focus:shadow-outline text-sm updatebutton" on:click={async () => await initializeEditor()}>
  Update
</button>
    <div class="min-w-[200px] overflow-y-auto bg-secondary h-full text-foreground text-sm flex flex-col pt-2" bind:this={sidebarContainer}></div>

    <div class="h-full w-full rounded-bl-lg bg-terminal-window-background p-0" bind:this={editorContainer}></div>
  </div>
</div>

<style>
  @keyframes blink {
    0% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0;
      transform: scale(0.8);
    }
    100% {
      opacity: 1;
      transform: scale(1);
    }
  }

  .animate-blink {
    animation: blink 1s ease-in-out infinite;
  }

  .animation-delay-200 {
    animation-delay: 0.2s;
  }

  .animation-delay-400 {
    animation-delay: 0.4s;
  }

.updatebutton {
  background-color: #4CAF50; /* Green */
  border: none;
  color: white;
  padding: 5px 10px; /* Adjusted padding for better spacing */
  text-align: center;
  text-decoration: none;
  display: block; /* Consider changing to 'block' if you want it to take its own line */
  position: absolute;
  top: 91%;
  font-size: 16px;
  margin: auto; /* Centers button if display is block */
  font-weight: bold;
  border-radius: 5px;
  cursor: pointer;

  transition: all .3s ease-in-out; /* Smooth transition for all properties */
}

.updatebutton:hover {
  background-color: #367C39; /* Slightly darker green on hover for a subtle effect */
  box-shadow: none; /* Remove box-shadow on hover for a cleaner look */
}

.updatebutton:focus {
  outline: none;
  box-shadow: none; /* Remove box-shadow on focus for a cleaner look */
}


</style>
