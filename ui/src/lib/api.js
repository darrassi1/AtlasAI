import {
  agentState,
  internet,
  modelList,
  projectList,
  messages,
  projectFiles,
  searchEngineList,
} from "./store";
import { io } from "socket.io-client";



const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://127.0.0.1:1337';
    } else {
      return `http://${host}:1337`;
    }
  } else {
    return 'http://127.0.0.1:1337';
  }
};

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getApiBaseUrl();
export const socket = io(API_BASE_URL);


export async function fetchInitialData() {
  const response = await fetch(`${API_BASE_URL}/api/data`);
  const data = await response.json();
  projectList.set(data.projects);
  modelList.set(data.models);
  searchEngineList.set(data.search_engines);
  localStorage.setItem("defaultData", JSON.stringify(data));
}

export async function fetchCodeSuggestionsapi(language, code) {
  const project_name = localStorage.getItem("selectedProject");
  const base_model = localStorage.getItem("selectedModel");
  const response = await fetch(`${API_BASE_URL}/api/code-suggestions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ language, code, project_name, base_model })
  });
  const data = await response.json();
  return data.suggestions;
}
export async function saveEditorContent(filename, content, projectName) {
  await fetch(`${API_BASE_URL}/api/codeeditorsave`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename: filename,
      content: content,
      project_name: projectName
    })
  });
}


export async function createProject(projectName) {
  await fetch(`${API_BASE_URL}/api/create-project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_name: projectName }),
  });
  projectList.update((projects) => [...projects, projectName]);
}


export async function saveChangeAPI(temperature,maxToken,topP) {
  const project_name = localStorage.getItem("selectedProject");
  const base_model = localStorage.getItem("selectedModel");
  await fetch(`${API_BASE_URL}/api/hyperparametre`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ temperature: temperature, maxToken: maxToken, topP:topP, project_name:project_name,base_model:base_model}),
  });
}
export async function deleteProject(projectName) {
  await fetch(`${API_BASE_URL}/api/delete-project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_name: projectName }),
  });
}

export async function fetchMessages() {
  const projectName = localStorage.getItem("selectedProject");
  const response = await fetch(`${API_BASE_URL}/api/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_name: projectName }),
  });
  const data = await response.json();
  messages.set(data.messages);
}

export async function fetchAgentState() {
  const projectName = localStorage.getItem("selectedProject");
  const response = await fetch(`${API_BASE_URL}/api/get-agent-state`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_name: projectName }),
  });
  const data = await response.json();
  agentState.set(data.state);
}

export async function executeAgent(prompt) {
  const projectName = localStorage.getItem("selectedProject");
  const modelId = localStorage.getItem("selectedModel");

  if (!modelId) {
    alert("Please select the LLM model first.");
    return;
  }

  await fetch(`${API_BASE_URL}/api/execute-agent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      prompt: prompt,
      base_model: modelId,
      project_name: projectName,
    }),
  });

  await fetchMessages();
}

export async function getBrowserSnapshot(snapshotPath) {
  const response = await fetch(`${API_BASE_URL}/api/browser-snapshot`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ snapshot_path: snapshotPath }),
  });
  const data = await response.json();
  return data.snapshot;
}

export async function fetchProjectFiles() {
  const projectName = localStorage.getItem("selectedProject");
  const response = await fetch(`${API_BASE_URL}/api/get-project-files?project_name=${projectName}`)
  const data = await response.json();
  projectFiles.set(data.files);
  return data.files;
}

export async function checkInternetStatus() {
  if (navigator.onLine) {
    internet.set(true);
  } else {
    internet.set(false);
  }
}

export async function fetchSettings() {
  const response = await fetch(`${API_BASE_URL}/api/settings`);
  const data = await response.json();
  return data.settings;
}

export async function updateSettings(settings) {
  await fetch(`${API_BASE_URL}/api/settings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });
}

export async function fetchLogs() {
  const response = await fetch(`${API_BASE_URL}/api/logs`);
  const data = await response.json();
  return data.logs;
}



export async function createFile(filename) {
  try {
    const projectName = localStorage.getItem("selectedProject");

    const response = await fetch(`${API_BASE_URL}/api/files/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ filename, projectName }),
    });

    if (!response.ok) {
      throw new Error('Failed to create file');
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating file:', error);
    throw error;
  }
}


export async function renameFile(oldName, newName) {
  try {
    const projectName = localStorage.getItem("selectedProject");

    const response = await fetch(`${API_BASE_URL}/api/files/rename`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ oldName, newName, projectName }),
    });

    if (!response.ok) {
      throw new Error('Failed to rename file');
    }
    let isInitializing = false;
    await initializeEditor();
    return await response.json();
  } catch (error) {
    console.error('Error renaming file:', error);
    throw error;
  }
}


export async function deleteFile(filename) {
  try {
    const projectName = localStorage.getItem("selectedProject");

    const response = await fetch(`${API_BASE_URL}/api/files/delete`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ filename, projectName }),
    });

    if (!response.ok) {
      throw new Error('Failed to delete file');
    }

    return await response.json();
  } catch (error) {
    console.error('Error deleting file:', error);
    throw error;
  }
}

export async function rectifyCodeAPI(code, prompt) {
  try {
    const project_name = localStorage.getItem("selectedProject");
    const base_model = localStorage.getItem("selectedModel");
    const response = await fetch(`${API_BASE_URL}/rectify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code, prompt, base_model ,project_name }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();
    return data.rectifiedCode;
  } catch (error) {
    console.error('Error in rectifyCode:', error);
    throw error; // Propagate the error back to the caller if needed
  }
}
