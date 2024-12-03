<script>
  import { onMount } from "svelte";
  import { projectList, isActive , modelList, internet, tokenUsage, agentState, messages, searchEngineList, storeSelectedProject} from "$lib/store";
  import { createProject, fetchMessages, fetchInitialData, deleteProject,fetchProjectFiles, fetchAgentState} from "$lib/api";  import { get } from "svelte/store";
  import Seperator from "./ui/Seperator.svelte";
  import DrawerWidget from "./DrawerWidget.svelte";

  let isHidden = false;
  let selectedProject;
  let selectedModel;
  let selectedSearchEngine;

  function toggleVisibility() {
    isHidden = !isHidden;
  }
function toggleMenu() {
  isActive.update(n => !n);
}
  const checkListAndSetItem = (list, itemKey, defaultItem) => {
    if (get(list) && get(list).length > 0) {
      const item = localStorage.getItem(itemKey);
      return item ? item : defaultItem;
    } else {
      localStorage.setItem(itemKey, "");
      return defaultItem;
    }
  };

  selectedProject = checkListAndSetItem( projectList, "selectedProject", "Select Project");
  selectedModel = checkListAndSetItem( modelList, "selectedModel", "Select Model");
  selectedSearchEngine = checkListAndSetItem( searchEngineList, "selectedSearchEngine", "Select Search Engine");

  function selectProject(project) {
    selectedProject = project;
    localStorage.setItem("selectedProject", project);
    storeSelectedProject.set(project);
    fetchMessages();
    fetchAgentState();
    fetchProjectFiles();
    document.getElementById("project-dropdown").classList.add("hidden");
  }
  function selectModel(model) {
    selectedModel = `${model[0]}`;
    localStorage.setItem("selectedModel", model[1]);
    document.getElementById("model-dropdown").classList.add("hidden");
  }
  function selectSearchEngine(searchEngine) {
    selectedSearchEngine = searchEngine;
    localStorage.setItem("selectedSearchEngine", searchEngine);
    document.getElementById("search-engine-dropdown").classList.add("hidden");
  }

  async function createNewProject() {
    const projectName = prompt('Enter the project name:');
    if (projectName) {
      await createProject(projectName);
      selectProject(projectName);
    }
  }
  async function deleteproject(project) {
    if (confirm(`Are you sure you want to delete ${project}?`)) {
      await deleteProject(project);
      await fetchInitialData();
      messages.set([]);
      agentState.set(null);
      tokenUsage.set(0);
      selectedProject = "Select Project";
      localStorage.setItem("selectedProject", "");
    }
  }

  const dropdowns = [
    { dropdown: "project-dropdown", button: "project-button" },
    { dropdown: "model-dropdown", button: "model-button" },
    { dropdown: "search-engine-dropdown", button: "search-engine-button" },
  ];
  function closeDropdowns(event) {
    dropdowns.forEach(({ dropdown, button }) => {
      const dropdownElement = document.getElementById(dropdown);
      const buttonElement = document.getElementById(button);

      if (
        dropdownElement &&
        buttonElement &&
        !dropdownElement.contains(event.target) &&
        !buttonElement.contains(event.target)
      ) {
        dropdownElement.classList.add("hidden");
      }
    });
  }
  onMount(() => {
    dropdowns.forEach(({ dropdown, button }) => {
      document.getElementById(button).addEventListener("click", function () {
        const dropdownElement = document.getElementById(dropdown);
        dropdownElement.classList.toggle("hidden");
      });
    });
    document.addEventListener("click", closeDropdowns);
    return () => {
      document.removeEventListener("click", closeDropdowns);
    };
  });

</script>
{#if isHidden}
        <button on:click={toggleVisibility} class="toggle-button-show">
  <i class={`fas ${isHidden ? 'fa-chevron-down' : 'fa-chevron-up'}`}></i>

</button>{/if}
{#if !isHidden}
<div class="control-panel border-b border-border bg-background pb-3">
  <div class="dropdown-menu relative inline-block">

    <button
      type="button"
      class="inline-flex items-center justify-between w-full text-foreground h-10 gap-2 px-3 py-2 text-sm min-w-[200px] bg-secondary rounded-md"
      id="project-button"
      aria-expanded="true"
      aria-haspopup="true"
    >
      <span id="selected-project">{selectedProject}</span>
      <i class="fas fa-angle-down text-tertiary"></i>
    </button>

    <div
      id="project-dropdown"
      class="absolute left-0 z-10 mt-2 min-w-[200px] origin-top-left rounded-xl bg-secondary shadow-lg max-h-96 overflow-y-auto hidden"
      role="menu"
      aria-orientation="vertical"
      aria-labelledby="project-button"
      tabindex="-1"
    >
      <div role="none" class="flex flex-col divide-y-2  w-full">
        <button
          class="flex gap-2 items-center text-sm px-4 py-3 w-full"
          on:click|preventDefault={createNewProject}
        >
          <i class="fas fa-plus"></i>
          new project
        </button>
        {#if $projectList !== null}
          {#each $projectList as project}
            <div
        class="flex items-center px-4 hover:bg-black/20 transition-colors {selectedProject === project ? 'bg-blue-200' : ''}">
              <button
                href="#"
                class="flex gap-2 items-center text-sm py-3 w-full h-full overflow-x-visible"
                on:click|preventDefault={() => selectProject(project)}
              >
                {project}
              </button>
              <button
                class="fa-regular fa-trash-can hover:text-red-600"
                on:click={() => deleteproject(project)}
                aria-label="Delete project"
              ></button>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
  <div
    class=""
    style="display: flex; align-items: center; gap: 20px"
  >
    <div class="flex items-center gap-2 text-sm">
      <span>Internet:</span>
      <span class=" size-3 rounded-full" class:online={$internet} class:offline={!$internet}></span>
    </div>

    <Seperator />
        <button on:click={toggleVisibility} class="toggle-button">
  <i class={`fas ${isHidden ? 'fa-chevron-down' : 'fa-chevron-up'}`}></i>
</button>
    <div class="flex items-center gap-2 text-sm">
      <span>Token Usage:</span>
      <span id="token-count" class="token-count-animation text-foreground">{$tokenUsage}</span>
    </div>

    <div class="relative inline-block text-left">
      <div>
        <button
          type="button"
          class="inline-flex items-center justify-between min-w-[200px] text-foreground w-fit gap-2 px-3 py-2 text-sm h-10 bg-secondary rounded-md"
          id="search-engine-button"
          aria-expanded="true"
          aria-haspopup="true"
        >
          <span id="selected-search-engine">{selectedSearchEngine}</span>
          <i class="fas fa-angle-down text-tertiary"></i>
        </button>
      </div>

<div
  id="search-engine-dropdown"
  class="absolute left-0 z-10 mt-2 origin-top-right min-w-[200px] bg-secondary rounded-xl shadow-lg max-h-96 overflow-y-auto hidden"
  role="menu"
  aria-orientation="vertical"
  aria-labelledby="search-engine-button"
  tabindex="-1"
>
  <div role="none" class="flex flex-col divide-y-2 w-full">
    {#if $searchEngineList !== null}
      {#each $searchEngineList as engine}
        <div
          class="flex items-center px-4 hover:bg-black/20 transition-colors
          {selectedSearchEngine === engine ? 'bg-gray-300' : ''}"
        >
          <button
            class="flex gap-2 items-center text-sm py-3 w-full text-clip"
            on:click|preventDefault={() => { selectSearchEngine(engine); localStorage.setItem('selectedSearchEngine', engine); }}
          >
            {engine}
          </button>
        </div>
      {/each}
    {/if}
  </div>
</div>
    </div>









    <div class="relative inline-block text-left">
      <div>
        <button
          type="button"
          class="inline-flex items-center text-foreground justify-between w-fit gap-x-1.5 min-w-[150px] px-3 py-2 text-sm h-10 bg-secondary rounded-md"
          id="model-button"
          aria-expanded="true"
          aria-haspopup="true"
        >
          <span id="selected-model">{selectedModel}</span>
          <i class="fas fa-angle-down text-tertiary"></i>
        </button>
      </div>

      <div
        id="model-dropdown"
        class="absolute right-0 z-10 mt-2 w-64 origin-top-right bg-secondary rounded-xl shadow-lg max-h-96 overflow-y-auto hidden"
        role="menu"
        aria-orientation="vertical"
        aria-labelledby="model-button"
        tabindex="-1"
      >
        {#if $modelList !== null}
          <div class="flex flex-col divide-y-2">
            {#each Object.entries($modelList) as [modelName, modelItems]}
              <div class="flex flex-col py-4 gap-2" role="none">
                <span class="text-sm px-4 w-full font-semibold"
                  >{modelName.toLowerCase()}</span
                >
                <div class="flex flex-col gap-[1px] px-6 w-full">
                  {#each modelItems as models}
                    <button
                      class="relative nav-button flex text-start text-sm text-clip hover:bg-black/20 px-2 py-1.5 rounded-md
                      transition-colors {selectedModel ===
                        `${models[0]} (${models[1]})` ||
                      selectedModel === models[0]
                        ? 'bg-gray-300'
                        : ''}"
                      on:click|preventDefault={() => selectModel(models)}
                    >
                      {models[0]}
                      <span class="tooltip text-[10px] px-2 text-gray-500"
                        >{models[1]}</span
                      >
                    </button>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <div class="relative inline-block text-left">
          <div class="settings-icon" on:click={toggleMenu}>
             <DrawerWidget />
  <i class="fas fa-cog"></i>
</div>

    </div>

  </div>
</div>
{/if}
<style>
    /* Styling for the toggle button */
  .toggle-button {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 40px;
    height: 40px;
    background-color: #f5f5f5;
    color: #333;

    border-radius: 40%;
    cursor: pointer;
    margin: 0 auto; /* Center the button */
  }
    .toggle-button-show{
    display: flex;

    justify-content: center;
    align-items: center;
    width: 5px;
    height: 5px;
    background-color: #f5f5f5;
    color: #333;

    border-radius: 40%;
    cursor: pointer;
    margin: -15px auto; /* Center the button */
  }
      .toggle-button-show:hover {
    background-color: #ddd;
  }
  .tooltip {
    font-size: 10px;
    background-color: black;
    color: white;
    text-align: center;
    border-radius: 100px;
    padding: 5px 10px;
    position: absolute;
    z-index: 1;
    opacity: 0;
    top: -20px;
    right: 0;
    transition: opacity 0.3s;
  }
  .nav-button:hover .tooltip {
    visibility: visible;
    opacity: 1;
  }

  @keyframes roll {
    0% {
      transform: translateY(-5%);
    }
    100% {
      transform: translateY(0);
    }
  }

  .online {
    background-color: #22c55e;
  }

  .offline {
    background-color: #ef4444;
  }

  .token-count-animation {
    display: inline-block;
    animation: roll 0.5s ease-in-out;
  }
  .toggle-button:hover {
    background-color: #ddd;
  }
  .control-panel {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    transition: max-height 0.3s ease-in-out;
    /*overflow-x: auto;*/



    padding: 0 0;

  }

.control-panel > * {
  flex-shrink: 0; /* Prevent items from shrinking */
  margin-right: 1px; /* Space between items */
}
/* Style for the scrollbar */
.control-panel::-webkit-scrollbar {
  height: 4px; /* Adjust scrollbar height */
}
</style>
