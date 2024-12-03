<script>
  import { isActive } from '../store';
  import { onDestroy } from 'svelte';
  import {saveChangeAPI} from "../api.js";

  let temperature = 1.0;
  let maxToken = 2048;
  let topP = 1.0;
  let active;

  const unsubscribe = isActive.subscribe(value => {
    active = value;
  });

  onDestroy(() => {
    unsubscribe();
  });

async function saveChanges() {
  try {
    await saveChangeAPI(temperature, maxToken, topP);
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}


function restoreDefaults() {
  // Set default values
  temperature = 1.0;
  maxToken = 2048;
  topP = 1.0;

  // Optionally, you can also trigger a save to the backend if needed
  saveChanges(); // Uncomment this if you want to save defaults immediately
}

</script>

<div id="settings-menu" class:active={active}>
  <div class="settings-header">
    <h2>Modify Settings</h2>
    <hr/>
  </div>
  <div class="settings-body">
    <div class="setting">
      <label for="temperature">Temperature</label>
      <input type="range" bind:value={temperature} min="0" max="1" step="0.1">
      <p>{temperature}</p>
    </div>
    <div class="setting">
      <label for="maxToken">Max Token</label>
      <input type="range" bind:value={maxToken} min="0" max="125000" step="0.1">
      <p>{maxToken}</p>
    </div>
    <div class="setting">
      <label for="topP">Top P</label>
      <input type="range" bind:value={topP} min="0" max="1" step="0.1">
      <p>{topP}</p>
    </div>
  </div>
  <div class="settings-footer">
    <button on:click={saveChanges}>Save changes</button>
    <button on:click={restoreDefaults}>Restore to defaults</button>
  </div>
</div>

<style>
  #settings-menu {
    position: fixed;
    right: 0;
    top: 60px;
    width: 300px;
    height: 100%;
    padding: 20px;
    background: var(--background);
    transition: transform 0.3s ease-in-out;
    transform: translateX(100%);
    z-index: 9999; /* Ensure the menu appears above other content */
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  }

  #settings-menu.active {
    transform: translateX(0);
  }

  .settings-header h2 {
    transition: color 0.3s ease-in-out;
  }

  .settings-body .setting label {
    transition: color 0.3s ease-in-out;
  }

.settings-footer button {
  border: none;
  color: white;
  padding: 2px 2px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  margin: 4px 2px;
  cursor: pointer;
}

.settings-footer button:nth-child(1) {
  background-color: #007BFF; /* Blue */
}

.settings-footer button:nth-child(1):hover {
  background-color: #0069D9; /* Darker blue */
}

.settings-footer button:nth-child(2) {
  background-color: #78dc35; /* Red */
}

.settings-footer button:nth-child(2):hover {
  background-color: #C82333; /* Darker red */
}

</style>
