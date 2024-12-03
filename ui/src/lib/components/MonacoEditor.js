import loader from "@monaco-editor/loader";
import {createFile, deleteFile, rectifyCodeAPI, renameFile, saveEditorContent, fetchCodeSuggestionsapi} from "../api.js";
import {Icons} from "../icons";




function getFileLanguage(fileType) {
  const fileTypeToLanguage = {
    js: "javascript",
    jsx: "javascript",
    ts: "typescript",
    tsx: "typescript",
    html: "html",
    css: "css",
    py: "python",
    java: "java",
    rb: "ruby",
    php: "php",
    cpp: "c++",
    c: "c",
    swift: "swift",
    kt: "kotlin",
    json: "json",
    xml: "xml",
    sql: "sql",
    sh: "shell",
  };
  return fileTypeToLanguage[fileType.toLowerCase()] || 'plaintext';
}
async function fetchCodeSuggestions(language, code) {
  return await fetchCodeSuggestionsapi(language, code);
}

export async function provideCompletionItems(monaco, model, position, language) {
  const word = model.getWordUntilPosition(position);
  const range = new monaco.Range(position.lineNumber, word.startColumn, position.lineNumber, word.endColumn);
  const codeBeforeCursor = model.getValueInRange(new monaco.Range(1, 1, position.lineNumber, position.column));
  //  const codeAfterCursor = model.getValueInRange(new monaco.Range(position.lineNumber, position.column, model.getLineCount(), model.getLineMaxColumn(model.getLineCount())));
  //   const suggestions = await fetchCodeSuggestions(language, `${codeBeforeCursor}${codeAfterCursor}`);
  const suggestions = await fetchCodeSuggestions(language, codeBeforeCursor);

  return {
    suggestions: suggestions.map(suggestion => ({
      label: suggestion.text,
      kind: monaco.languages.CompletionItemKind.Snippet,
      insertText: suggestion.text,
      range: range,
      documentation: suggestion.documentation || 'Auto-completion suggestion',
      detail: suggestion.detail || 'Suggested by AI'
    }))
  };
}


const getTheme = () => {
  const theme = localStorage.getItem("mode-watcher-mode");
  return theme === "light" ? "vs-light" : "vs-dark";
};

export async function initializeMonaco() {
  const monacoEditor = await import("monaco-editor");
  loader.config({ monaco: monacoEditor.default });
  return loader.init();
}
const completionProviderDisposables = [];

const registerCompletionProvider = (monaco, language) => {
  if (completionProviderDisposables[language]) {
    completionProviderDisposables[language].dispose();
  }

  const disposable = monaco.languages.registerCompletionItemProvider(language, {
    provideCompletionItems: (model, position) => provideCompletionItems(monaco, model, position, language)
  });

  completionProviderDisposables[language] = disposable;
  return disposable;
};

export const deregisterCompletionProviders = () => {
  Object.values(completionProviderDisposables).forEach(disposable => disposable.dispose());
  Object.keys(completionProviderDisposables).forEach(key => delete completionProviderDisposables[key]);
};

export async function initializeEditorRef(monaco, container) {
  const editor = monaco.editor.create(container, {
    theme: getTheme(),
    readOnly: false,
    automaticLayout: true,
    language: 'javascript' // Default language, will be dynamically changed
       // minimap: { enabled: false }, // Disable minimap for cleaner UI
    //scrollbar: {
     // vertical: 'auto',
    //  horizontal: 'auto'
   // },
  });



  return editor;
}

export function initializeRectifyFeature(editor) {
  editor.onDidChangeCursorSelection((e) => {
    const selection = editor.getSelection();
    const selectedText = editor.getModel().getValueInRange(selection);

    if (selectedText) {
      showRectifyPopup(editor, selectedText, selection);
    }
  });
}

function showRectifyPopup(editor, selectedText, selection) {
  let menu; // Declare menu here so it can be accessed in multiple functions

  const content = document.createElement("div");
  content.style.display = "flex";
  content.style.flexDirection = "column";
  content.style.gap = "2px";

  const header = document.createElement("div");
  header.style.display = "flex";
  header.style.justifyContent = "space-between";
  header.style.alignItems = "center";

  const headerTitle = document.createElement("span");
  headerTitle.textContent = "Voici une autre façon d'écrire ceci";
  headerTitle.style.fontWeight = "bold";

  const closeButton = document.createElement("button");
  closeButton.innerHTML = "ㄨ"; // Close icon
  closeButton.style.background = "none";
  closeButton.style.border = "none";
  closeButton.style.fontSize = "20px";
  closeButton.style.cursor = "pointer";
  closeButton.addEventListener("click", () => {
    document.body.removeChild(popup);
  });

  header.appendChild(headerTitle);
  header.appendChild(closeButton);

  const promptInput = document.createElement("input");
  promptInput.placeholder = "Enter prompt (optional)";
  promptInput.style.width = "100%";
  promptInput.style.padding = "5px";
  promptInput.style.marginBottom = "5px";
  promptInput.style.boxSizing = "border-box";
  promptInput.style.borderRadius = "3px";
  promptInput.style.border = "1px solid #ccc";

  const codeInput = document.createElement("textarea");
  codeInput.value = selectedText;
  codeInput.style.width = "100%";
  codeInput.style.height = "100px";
  codeInput.style.fontFamily = "monospace";
  codeInput.style.whiteSpace = "pre";
  codeInput.style.padding = "2px";
  codeInput.style.boxSizing = "border-box";
  codeInput.style.borderRadius = "3px";
  codeInput.style.border = "1px solid #ccc";
const buttonsContainer = document.createElement("div");


const retryButton = document.createElement("button");
retryButton.innerHTML = "↻"; // Retry icon
retryButton.style.padding = "2px 5px";
retryButton.style.marginLeft = "5px"; // Add right margin to create space between buttons
retryButton.style.border = "none";
retryButton.style.borderRadius = "3px";
retryButton.style.background = "#f0f0f0";
retryButton.style.cursor = "pointer";

const validateButton = document.createElement("button");
validateButton.textContent = "⤴ Remplacer";
validateButton.style.padding = "0px 5px";
validateButton.style.marginRight = "5px"; // Add right margin to create space between buttons
validateButton.style.border = "none";
validateButton.style.borderRadius = "3px";
validateButton.style.background = "#4CAF50";
validateButton.style.color = "#fff";
validateButton.style.cursor = "pointer";

const settingsButton = document.createElement("button");
settingsButton.innerHTML = "⚙️ Regler"; // Settings icon
settingsButton.style.padding = "2px 5px";
settingsButton.style.border = "none";
settingsButton.style.borderRadius = "3px";
settingsButton.style.background = "#f0f0f0";
settingsButton.style.cursor = "pointer";

content.appendChild(header);
content.appendChild(promptInput);
content.appendChild(codeInput);
buttonsContainer.appendChild(validateButton);
buttonsContainer.appendChild(settingsButton);
buttonsContainer.appendChild(retryButton);

content.appendChild(buttonsContainer);

  const popup = createPopup(content, {
    width: "500px",
    height: "250px",
    top: "20%",
    left: "5%",
  });

  settingsButton.addEventListener("click", () => {
    if (!buttonsContainer.contains(menu)) {
      menu = createSettingsMenu();
      buttonsContainer.appendChild(menu);
    } else {
      menu.remove();
    }
  });

  retryButton.addEventListener("click", async () => {
    const prompt = promptInput.value;
    const rectifiedText = await rectifyCode(selectedText, prompt);
    codeInput.value = rectifiedText;
  });

  validateButton.addEventListener("click", async () => {
    const rectifiedText = codeInput.value;
    editor.executeEdits("rectify", [{ range: selection, text: rectifiedText }]);
    document.body.removeChild(popup);
  });
}

function createSettingsMenu() {
  const menu = document.createElement("div");
  menu.style.display = "flex";
  menu.style.flexDirection = "column";
  menu.style.gap = "10px";
  menu.style.padding = "10px";
  menu.style.border = "1px solid #ccc";
  menu.style.borderRadius = "3px";
  menu.style.background = "#fff";
  menu.style.boxShadow = "0 2px 10px rgba(0, 0, 0, 0.1)";
  menu.style.position = "absolute";
  menu.style.top = "0";
  menu.style.right = "0";
  menu.style.width = "200px";
  menu.style.zIndex = "1001";

  const closeButton = document.createElement("button");
  closeButton.textContent = "Close";
  closeButton.style.padding = "5px 10px";
  closeButton.style.border = "none";
  closeButton.style.borderRadius = "3px";
  closeButton.style.background = "#f0f0f0";
  closeButton.style.cursor = "pointer";
  closeButton.addEventListener("click", () => {
    menu.remove();
  });

  const toneLabel = document.createElement("div");
  toneLabel.textContent = "Ton :";
  toneLabel.style.fontWeight = "bold";

  const toneSelect = document.createElement("select");
  const tones = ["Professionnel", "Décontracté", "Enthousiaste", "Informatif", "Drôle"];
  tones.forEach(tone => {
    const option = document.createElement("option");
    option.value = tone;
    option.textContent = tone;
    toneSelect.appendChild(option);
  });

  const formatLabel = document.createElement("div");
  formatLabel.textContent = "Format :";
  formatLabel.style.fontWeight = "bold";

  const formatSelect = document.createElement("select");
  const formats = ["Paragraphe", "Email", "Idées", "Article de blog"];
  formats.forEach(format => {
    const option = document.createElement("option");
    option.value = format;
    option.textContent = format;
    formatSelect.appendChild(option);
  });

  const lengthLabel = document.createElement("div");
  lengthLabel.textContent = "Longueur :";
  lengthLabel.style.fontWeight = "bold";

  const lengthSelect = document.createElement("select");
  const lengths = ["Court", "Moyen", "Long"];
  lengths.forEach(length => {
    const option = document.createElement("option");
    option.value = length;
    option.textContent = length;
    lengthSelect.appendChild(option);
  });

  menu.appendChild(closeButton);
  menu.appendChild(toneLabel);
  menu.appendChild(toneSelect);
  menu.appendChild(formatLabel);
  menu.appendChild(formatSelect);
  menu.appendChild(lengthLabel);
  menu.appendChild(lengthSelect);

  return menu;
}

function createPopup(content, options = {}) {
  const popup = document.createElement("div");
  popup.style.position = "fixed";
  popup.style.width = options.width || "80%";
  popup.style.height = options.height || "80%";
  popup.style.top = options.top || "10%";
  popup.style.left = options.left || "10%";
  popup.style.backgroundColor = "#fff";
  popup.style.border = "1px solid #ccc";
  popup.style.boxShadow = "0 2px 10px rgba(0, 0, 0, 0.1)";
  popup.style.borderRadius = "5px";
  popup.style.padding = "15px";
  popup.style.overflow = "auto";
  popup.style.zIndex = "1000";
  popup.style.resize = "both";

  popup.appendChild(content);

  document.addEventListener("mousedown", outsideClickListener);

function outsideClickListener(event) {
  if (!popup.contains(event.target)) {
    // Vérifier si le popup est toujours un enfant de document.body
    if (document.body.contains(popup)) {
      document.body.removeChild(popup);
    }
    // Dans tous les cas, supprimer l'écouteur d'événements
    document.removeEventListener("mousedown", outsideClickListener);
  }
}

  document.body.appendChild(popup);

  return popup;
}


async function rectifyCode(code, prompt) {

  return await rectifyCodeAPI(code, prompt);
}






export function createModel(monaco, file, projectName, editor, autocompletionEnabled) {
  const language = getFileLanguage(file.file.split(".").pop());
  const model = monaco.editor.createModel(file.code, language);

  editor.setModel(model);

  editor.onDidChangeModelContent(() => {
    const currentContent = model.getValue();
    saveEditorContent(file.file, currentContent, projectName);
  });

  // Register the completion provider for the detected language
  if (autocompletionEnabled) {
    // Register the completion provider for the detected language
    registerCompletionProvider(monaco, language);
  } else {
    // Deregister autocompletion providers if they exist
    deregisterCompletionProviders();
  }

  return model;
}

export function disposeEditor(editor) {
  if (editor) editor.dispose();
}

export function enableTabSwitching(editor, models, tabContainer) {
  Object.keys(models).forEach((filename, index) => {
    const tabElement = document.createElement("div");
    tabElement.textContent = filename.split(/[\/\\]/).pop();
    tabElement.className =
      "tab p-2 me-2 rounded-lg text-sm cursor-pointer hover:bg-secondary text-primary whitespace-nowrap";
    tabElement.setAttribute("data-filename", filename);
    tabElement.addEventListener("click", () =>
      switchTab(editor, models, filename, tabElement)
    );
    tabContainer.appendChild(tabElement);
    if (index === Object.keys(models).length - 1) {
      tabElement.classList.add("bg-secondary");
    }

  });
}

function switchTab(editor, models, filename, tabElement) {
  Object.entries(models).forEach(([file, model]) => {
    if (file === filename) {
      editor.setModel(model);
    }
  });

  const allTabElements = tabElement?.parentElement?.children;
  for (let i = 0; i < allTabElements?.length; i++) {
    allTabElements[i].classList.remove("bg-secondary");
  }

  tabElement.classList.add("bg-secondary");
}

export function disposeTabContainer(tabContainer) {
  // Remove all child elements from the tabContainer
  while (tabContainer.firstChild) {
    tabContainer.removeChild(tabContainer.firstChild);
  }
}

export function disposeSidebar(sidebarContainer) {
  // Remove all child elements from the sidebarContainer
  while (sidebarContainer.firstChild) {
    sidebarContainer.removeChild(sidebarContainer.firstChild);
  }
}

export function sidebar(editor, models, sidebarContainer) {
  const folders = {};

  // Add CSS styles dynamically
  const addStyles = () => {
    const style = document.createElement("style");
    style.textContent = `
      .sidebar {
        overflow-y: auto;
        max-height: 20vh;
        padding: 10px;
        background-color: #fff;
        border-right: 1px solid #ddd;
      }

      .sidebar-element {
        cursor: pointer;
        display: flex-wrap;
        align-items: center;
        padding: 5px;
        border: 1px solid #ddd;
        border-radius: 4px;
        margin-bottom: 2px;
        background-color: #f9f9f9;
        transition: background-color 0.3s;
      }

      .sidebar-element:hover {
        background-color: #e9e9e9;
      }

      .sidebar-element .name-element {
        display: flex;
        align-items: center;
        gap: 1px;
      }

      .sidebar-element .action-btn {
        cursor: pointer;
        margin-left: 10px;
        background: none;
        border: none;
        color: #555;
        transition: color 0.3s;
      }

      .sidebar-element .action-btn:hover {
        color: #000;
      }

      .sidebar-element[data-expanded="true"] > .child-elements {
        display: block;
      }

      .sidebar-element[data-expanded="false"] > .child-elements {
        display: none;
      }

      .child-elements {
        margin-left: 10px; /* Indent child elements */
        border-left: 1px dashed #ddd;
        padding-left: 1px;
        border: 1px solid black;
      }

      .action-btn {
        display: flex;
        align-items: center;
        padding: 2px 5px;
        border-radius: 3px;
        transition: background-color 0.3s;
      }

      .action-btn:hover {
        background-color: #ddd;
      }

      button.action-btn {
        border: none;
        background: none;
        cursor: pointer;
      }

      .sidebar-header {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 10px;
      }

      .sidebar-footer {
        margin-top: 10px;
      }
    `;
    document.head.appendChild(style);
  };

  addStyles();

  const toggleFolder = (folderElement) => {
    const isExpanded = folderElement.getAttribute('data-expanded') === 'true';
    folderElement.setAttribute('data-expanded', !isExpanded);
  };

  const openFileInEditor = (filename) => {
    if (models[filename]) {
      editor.setModel(models[filename]);
    }
  };

// Function to create sidebar elements
// Function to create sidebar elements
const createSidebarElement = (fullPath, isFolder, level = 0) => {
  const parts = fullPath.split(/[\/\\]/);
  const filename = parts[parts.length - 1]; // Get the last part as the filename
  const sidebarElement = document.createElement("div");
  sidebarElement.classList.add("sidebar-element", "flex", "items-center", "justify-between");
  sidebarElement.style.paddingLeft = `${level * 10}px`;

  const nameContainer = document.createElement("div");
  nameContainer.classList.add("flex", "items-center", "gap-2");

  const iconElement = document.createElement("span");
  iconElement.innerHTML = isFolder ? Icons.Folder : Icons.File;

  const filenameText = document.createElement("span");
  filenameText.classList.add("filename-text");
  filenameText.textContent = filename; // Use filename only for display

  nameContainer.appendChild(iconElement);
  nameContainer.appendChild(filenameText);

  const actionsContainer = document.createElement("div");
  actionsContainer.classList.add("flex", "items-center", "gap-2");

  const renameButton = document.createElement("button");
  renameButton.innerHTML = Icons.Rename;
  renameButton.classList.add("action-btn");
  renameButton.addEventListener('click', (event) => {
    event.stopPropagation();
    filenameText.contentEditable = true;
    filenameText.focus();
    filenameText.addEventListener('blur', () => {
      filenameText.contentEditable = false;
      const newFilename = filenameText.textContent.trim();
      const newFullPath = parts.slice(0, parts.length - 1).join('/') + '/' + newFilename; // Construct new full path
      renameFileAPI(fullPath, newFullPath);
    });
  });

  const deleteButton = document.createElement("button");
  deleteButton.innerHTML = Icons.Delete;
  deleteButton.classList.add("action-btn");
  deleteButton.addEventListener('click', (event) => {
    event.stopPropagation();
    deleteFileAPI(fullPath); // Pass full path for deletion
  });

  actionsContainer.appendChild(renameButton);
  actionsContainer.appendChild(deleteButton);

  sidebarElement.appendChild(nameContainer);
  sidebarElement.appendChild(actionsContainer);

  if (isFolder) {
    sidebarElement.setAttribute('data-expanded', 'false');
    nameContainer.addEventListener('click', (event) => {
      event.stopPropagation();
      toggleFolder(sidebarElement);
    });
  } else {
    sidebarElement.addEventListener('click', (event) => {
      event.stopPropagation();
      openFileInEditor(fullPath); // Pass full path for opening file
    });
  }

  return sidebarElement;
};

  const changeTabColor = (index) => {
    const allTabElements = document.querySelectorAll("#tabContainer")[0].children;
    for (let i = 0; i < allTabElements?.length; i++) {
      allTabElements[i].classList.remove("bg-secondary");
    }
    allTabElements[index].classList.add("bg-secondary");
  };


// Function to populate sidebar based on current models
const populateSidebar = async () => {
  try {
    // Clear sidebar content
    sidebarContainer.innerHTML = '';

    // Helper object to keep track of folders
    const folders = {};

    // Iterate through models and update sidebar
    for (const [filename, model] of Object.entries(models)) {
      const fullPath = filename; // Assuming filename already contains full path
      const parts = fullPath.split(/[\/\\]/);
      let currentFolder = sidebarContainer;

      for (let index = 0; index < parts.length; index++) {
        const currentPath = parts.slice(0, index + 1).join('/');

        // Check if it's the last part (file)
        if (index === parts.length - 1) {
          const fileElement = createSidebarElement(fullPath, model.isFolder, index);
          fileElement.addEventListener("click", () => {
            editor.setModel(model);
            changeTabColor(Object.keys(models).indexOf(filename));
          });
          currentFolder.appendChild(fileElement);
        } else {
          const folderName = parts.slice(0, index + 1).join('/');
          if (!folders[folderName]) {
            const folderElement = createSidebarElement(folderName, true, index);
            const childContainer = document.createElement("div");
            childContainer.classList.add("child-elements");
            folderElement.appendChild(childContainer);
            currentFolder.appendChild(folderElement);
            folders[folderName] = childContainer;
            currentFolder = childContainer;
          } else {
            currentFolder = folders[folderName];
          }
        }
      }
    }

    // Set the first model as the active model if any models exist
    const modelArray = Object.values(models);
    if (modelArray.length > 0) {
      editor.setModel(modelArray[0]);
    }
  } catch (error) {
    console.error('Error populating sidebar:', error);
    // Handle error (e.g., display error message to user)
  }
};

// Function to handle renaming a file
const renameFileAPI = async (oldPath, newPath) => {
  try {
    await renameFile(oldPath, newPath); // Assuming renameFile handles the API call and renaming
    models[newPath] = models[oldPath];
    delete models[oldPath];
    populateSidebar(); // Refresh sidebar after renaming
  } catch (error) {
    console.error('Error renaming file:', error);
    // Handle error (e.g., show error message to user)
  }
};

// Function to handle deleting a file
// Function to handle deleting a file or folder recursively
const deleteFileAPI = async (filePath) => {
  try {
    // Recursively delete all children if it's a folder
    if (models[filePath]?.isFolder) {
      const filesToDelete = Object.keys(models).filter(filename => filename.startsWith(filePath));
      for (const file of filesToDelete) {
        await deleteFile(file); // Assuming deleteFile is a function that handles the API call
        delete models[file];
      }
    } else {
      await deleteFile(filePath); // Assuming deleteFile is a function that handles the API call
      delete models[filePath];
    }

    populateSidebar(); // Refresh sidebar after deletion
  } catch (error) {
    console.error('Error deleting file:', error);
    // Handle error (e.g., show error message to user)
  }
};


// Function to create a new file
const createNewFile = async () => {
  const newFileName = "newFile.js"; // Default name, can be changed later by the user
  if (!models[newFileName]) {
    models[newFileName] = monaco.editor.createModel("", "javascript");
    populateSidebar(); // Refresh sidebar after creating new file

    try {
      await createFile(newFileName); // Assuming createFile handles the API call and creation
    } catch (error) {
      console.error('Error creating file:', error);
    }
  }
};

// Initialize sidebar on page load
populateSidebar();

// Create file button
const createFileButton = document.createElement("button");
createFileButton.innerHTML = Icons.Create;
createFileButton.classList.add("action-btn");
createFileButton.addEventListener("click", createNewFile);
sidebarContainer.appendChild(createFileButton);

// Visualize files button
const visualizeFilesButton = document.createElement("button");
visualizeFilesButton.innerHTML = "Visualize Files";
visualizeFilesButton.classList.add("action-btn");
visualizeFilesButton.addEventListener("click", () => {
  const popup = document.createElement("div");
  popup.style.position = "fixed";
  popup.style.width = "80%";
  popup.style.height = "80%";
  popup.style.top = "10%";
  popup.style.left = "10%";
  popup.style.backgroundColor = "#fff";
  popup.style.border = "1px solid #000";
  popup.style.padding = "10px";
  popup.style.overflow = "auto";
  popup.style.zIndex = "1000";

  const closeButton = document.createElement("button");
  closeButton.textContent = "Close";
  closeButton.addEventListener("click", () => {
    document.body.removeChild(popup);
  });
  popup.appendChild(closeButton);

  const fileList = document.createElement("ul");
  Object.keys(models).forEach((filename) => {
    const fileItem = document.createElement("li");
    fileItem.textContent = filename;
    fileItem.style.cursor = "pointer";
    fileItem.addEventListener("click", () => {
      openFileInEditor(filename);
      document.body.removeChild(popup);
    });
    fileList.appendChild(fileItem);
  });
  popup.appendChild(fileList);

  document.body.appendChild(popup);
});
sidebarContainer.appendChild(visualizeFilesButton);



}
