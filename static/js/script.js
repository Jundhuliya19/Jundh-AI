// ========================================
// JUNDH AI 3.0
// MAIN JAVASCRIPT
// ========================================

const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

const attachBtn = document.getElementById("attach-btn");
const fileInput = document.getElementById("file-input");

const filePreview = document.getElementById("file-preview");
const previewContent = document.getElementById("preview-content");
const removeFileBtn = document.getElementById("remove-file-btn");

const typingIndicator = document.getElementById("typing-indicator");

const newChatBtn = document.getElementById("new-chat-btn");
const clearChatBtn = document.getElementById("clear-chat-btn");

const themeBtn = document.getElementById("theme-btn");

const voiceBtn = document.getElementById("voice-btn");

const menuBtn = document.getElementById("menu-btn");
const sidebar = document.getElementById("sidebar");

const webSearchToggle = document.getElementById("web-search-toggle");

const modeButtons = document.querySelectorAll(".mode-btn");

const modeDescription = document.getElementById("mode-description");

let selectedFile = null;

let currentMode = "chat";

let activeChatId = null;


// ========================================
// SEND BUTTON
// ========================================

sendBtn.addEventListener("click", sendMessage);


// ========================================
// ENTER TO SEND
// SHIFT + ENTER FOR NEW LINE
// ========================================

userInput.addEventListener("keydown", function (event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        sendMessage();
    }
});


// ========================================
// AUTO RESIZE TEXTAREA
// ========================================

userInput.addEventListener("input", function () {

    this.style.height = "auto";

    this.style.height =
        Math.min(
            this.scrollHeight,
            160
        ) + "px";
});


// ========================================
// SUGGESTION BUTTONS
// ========================================

document.querySelectorAll(".suggestion")
    .forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                userInput.value =
                    button.textContent.trim();

                userInput.focus();
            }
        );

    });


// ========================================
// FILE UPLOAD BUTTON
// ========================================

attachBtn.addEventListener("click", function () {

    fileInput.accept =
        "image/png,image/jpeg,image/webp,application/pdf";

    fileInput.click();

});


// ========================================
// FILE SELECTED
// ========================================

fileInput.addEventListener("change", function () {

    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    selectedFile = file;

    showFilePreview(file);

});


// ========================================
// SHOW FILE PREVIEW
// ========================================

function showFilePreview(file) {

    filePreview.classList.remove("hidden");

    previewContent.innerHTML = "";


    // IMAGE PREVIEW

    if (file.type.startsWith("image/")) {

        const image = document.createElement("img");

        image.src =
            URL.createObjectURL(file);

        image.className =
            "preview-image";

        previewContent.appendChild(image);
    }


    // FILE NAME

    const fileName =
        document.createElement("span");

    fileName.textContent =
        file.name;

    previewContent.appendChild(fileName);

}


// ========================================
// REMOVE FILE
// ========================================

removeFileBtn.addEventListener(
    "click",
    clearSelectedFile
);


function clearSelectedFile() {

    selectedFile = null;

    fileInput.value = "";

    previewContent.innerHTML = "";

    filePreview.classList.add("hidden");

}


// ========================================
// SEND MESSAGE
// ========================================

async function sendMessage() {

    const message =
        userInput.value.trim();


    if (
        message === "" &&
        !selectedFile
    ) {

        return;
    }


    // IMAGE GENERATION MODE IS NOT
    // CONNECTED TO BACKEND YET

   if (currentMode === "image") {

    if (message === "") {
        return;
    }

    addUserMessage(message, null);

    userInput.value = "";
    userInput.style.height = "auto";

    showTyping();

    try {

        const response = await fetch(
            "/generate-image",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    prompt: message
                })
            }
        );


        const data = await response.json();

        hideTyping();


        if (!response.ok) {

            addAIMessage(
                "⚠️ " +
                (
                    data.error ||
                    "Image generation failed."
                )
            );

            return;
        }


        addGeneratedImage(
            data.response,
            data.image_url
        );

    }

    catch (error) {

        hideTyping();

        console.error(
            "Image Generation Error:",
            error
        );

        addAIMessage(
            "⚠️ Could not connect to the image-generation server."
        );

    }

    return;
}


    const fileToSend =
        selectedFile;


    // DISPLAY USER MESSAGE

    addUserMessage(
        message,
        fileToSend
    );


    // CLEAR INPUT

    userInput.value = "";

    userInput.style.height = "auto";

    clearSelectedFile();


    // SHOW TYPING

    showTyping();


    // FORM DATA

    const formData =
        new FormData();


    formData.append(
        "message",
        message
    );
    
    if (activeChatId) {

    formData.append(
        "chat_id",
        activeChatId
    );

}

    formData.append(
    "web_search",
    webSearchToggle.checked
        ? "true"
        : "false"
);


    // ATTACH FILE

    if (fileToSend) {

        if (
            fileToSend.type ===
            "application/pdf"
        ) {

            formData.append(
                "pdf",
                fileToSend
            );

        }

        else if (
            fileToSend.type
                .startsWith("image/")
        ) {

            formData.append(
                "image",
                fileToSend
            );

        }

    }


    try {

        const response =
            await fetch(
                "/chat",
                {
                    method: "POST",

                    body: formData
                }
            );


        const data =
            await response.json();


        hideTyping();


        if (!response.ok) {

            addAIMessage(
                data.response ||
                "Something went wrong."
            );

            return;
        }


        addAIMessage(
            data.response
        );
        
        await loadChatList();
    }

    catch (error) {

        hideTyping();

        console.error(
            "Jundh AI Error:",
            error
        );


        addAIMessage(
            "⚠️ I couldn't connect to the Jundh AI server. Check whether Flask is running and try again."
        );

    }

}


// ========================================
// ADD USER MESSAGE
// ========================================

function addUserMessage(
    message,
    file
) {

    removeWelcomeScreen();


    const row =
        document.createElement("div");

    row.className =
        "message-row user";


    const avatar =
        document.createElement("div");

    avatar.className =
        "message-avatar";

    avatar.textContent =
        "You";


    const bubble =
        document.createElement("div");

    bubble.className =
        "message-bubble";


    // SHOW UPLOADED IMAGE

    if (
        file &&
        file.type.startsWith("image/")
    ) {

        const image =
            document.createElement("img");

        image.src =
            URL.createObjectURL(file);

        image.className =
            "chat-uploaded-image";

        bubble.appendChild(image);

    }


    // SHOW PDF NAME

    if (
        file &&
        file.type === "application/pdf"
    ) {

        const pdfLabel =
            document.createElement("p");

        pdfLabel.textContent =
            "📄 " + file.name;

        bubble.appendChild(pdfLabel);

    }


    // USER TEXT

    if (message) {

        const text =
            document.createElement("p");

        text.textContent =
            message;

        bubble.appendChild(text);

    }


    row.appendChild(avatar);

    row.appendChild(bubble);

    chatBox.appendChild(row);


    scrollToBottom();

}


// ========================================
// ADD AI MESSAGE
// ========================================

function addAIMessage(message) {

    removeWelcomeScreen();


    const row =
        document.createElement("div");

    row.className =
        "message-row ai";


    const avatar =
        document.createElement("div");

    avatar.className =
        "message-avatar";

    avatar.textContent =
        "J";


    const bubble =
        document.createElement("div");

    bubble.className =
        "message-bubble";


    // MARKDOWN SUPPORT

    if (
        typeof marked !== "undefined"
    ) {

        bubble.innerHTML =
            marked.parse(message);

    }

    else {

        bubble.textContent =
            message;

    }


    row.appendChild(avatar);

    row.appendChild(bubble);

    chatBox.appendChild(row);


    scrollToBottom();

}


// ========================================
// REMOVE WELCOME SCREEN
// ========================================

function removeWelcomeScreen() {

    const welcomeScreen =
        document.getElementById(
            "welcome-screen"
        );


    if (welcomeScreen) {

        welcomeScreen.remove();

    }

}


// ========================================
// TYPING INDICATOR
// ========================================

function showTyping() {

    typingIndicator
        .classList
        .remove("hidden");

}


function hideTyping() {

    typingIndicator
        .classList
        .add("hidden");

}


// ========================================
// SCROLL
// ========================================

function scrollToBottom() {

    chatBox.scrollTop =
        chatBox.scrollHeight;

}


// ========================================
// NEW CHAT
// ========================================

newChatBtn.addEventListener(
    "click",
    async function () {

        try {

            const response =
                await fetch(
                    "/chats/new",
                    {
                        method: "POST"
                    }
                );

            const data =
                await response.json();


            if (!response.ok) {

                console.error(
                    "New chat error:",
                    data
                );

                return;
            }


            activeChatId =
                data.chat_id;


            // CLEAR CHAT SCREEN

            chatBox.innerHTML = "";


            // SHOW A SIMPLE EMPTY CHAT MESSAGE

            addAIMessage(
                "New chat started. How can I help you?"
            );


            // RESET INPUT AND FILE

            userInput.value = "";

            clearSelectedFile();


            // RELOAD SIDEBAR CHAT LIST

            await loadChatList();


            // FOCUS MESSAGE BOX

            userInput.focus();


            if (window.innerWidth <= 720) {

                sidebar.classList.remove(
                    "open"
                );

            }

        }

        catch (error) {

            console.error(
                "Create new chat error:",
                error
            );

        }

    }
);


// ========================================
// CLEAR CHAT
// ========================================

clearChatBtn.addEventListener(
    "click",
    clearConversation
);


async function clearConversation() {

    if (!activeChatId) {

        addAIMessage(
            "No active conversation selected."
        );

        return;
    }


    try {

        const response = await fetch(
            "/clear",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    chat_id: activeChatId
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            console.error(
                "Clear chat error:",
                data
            );

            return;
        }


        chatBox.innerHTML = "";

        addAIMessage(
            "Conversation cleared. How can I help you?"
        );


    } catch (error) {

        console.error(
            "Clear conversation error:",
            error
        );

    }

}


// ========================================
// THEME SWITCH
// ========================================

themeBtn.addEventListener(
    "click",
    function () {

        document.body
            .classList
            .toggle("light-mode");


        const isLight =
            document.body
                .classList
                .contains(
                    "light-mode"
                );


        localStorage.setItem(
            "jundh-theme",
            isLight
                ? "light"
                : "dark"
        );

    }
);


// LOAD SAVED THEME

const savedTheme =
    localStorage.getItem(
        "jundh-theme"
    );


if (savedTheme === "light") {

    document.body
        .classList
        .add("light-mode");

}


// ========================================
// MOBILE SIDEBAR
// ========================================

menuBtn.addEventListener(
    "click",
    function () {

        sidebar.classList
            .toggle("open");

    }
);


// ========================================
// MODES
// ========================================

modeButtons.forEach(
    function (button) {

        button.addEventListener(
            "click",
            function () {

                modeButtons.forEach(
                    function (item) {

                        item.classList
                            .remove("active");

                    }
                );


                button.classList
                    .add("active");


                currentMode =
                    button.dataset.mode;


                if (
                    currentMode === "chat"
                ) {

                    modeDescription.textContent =
                        "AI chat with image and document understanding";

                    userInput.placeholder =
                        "Message Jundh AI...";

                }


                if (
                    currentMode === "image"
                ) {

                    modeDescription.textContent =
                        "Create images from text prompts";

                    userInput.placeholder =
                        "Describe the image you want to create...";

                }


                if (
                    window.innerWidth <= 720
                ) {

                    sidebar.classList
                        .remove("open");

                }

            }
        );

    }
);


// ========================================
// VOICE INPUT
// ========================================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


voiceBtn.addEventListener(
    "click",
    function () {


        if (!SpeechRecognition) {

            alert(
                "Voice recognition is not supported in this browser. Try Chrome or Edge."
            );

            return;
        }


        const recognition =
            new SpeechRecognition();


        recognition.lang =
            "en-IN";


        recognition.interimResults =
            false;


        recognition.continuous =
            false;


        voiceBtn.textContent =
            "🔴";


        recognition.start();


        recognition.onresult =
            function (event) {

                const transcript =
                    event.results[0][0]
                        .transcript;


                userInput.value =
                    transcript;


                userInput.focus();

            };


        recognition.onend =
            function () {

                voiceBtn.textContent =
                    "🎤";

            };


        recognition.onerror =
            function () {

                voiceBtn.textContent =
                    "🎤";

            };

    }
);

// ========================================
// SIDEBAR TOOL BUTTONS
// ========================================

const imageToolBtn =
    document.getElementById("image-tool-btn");

const pdfToolBtn =
    document.getElementById("pdf-tool-btn");

const voiceToolBtn =
    document.getElementById("voice-tool-btn");

const webToolBtn =
    document.getElementById("web-tool-btn");


// IMAGE ANALYSIS

imageToolBtn.addEventListener("click", function () {

    fileInput.accept =
        "image/png,image/jpeg,image/webp";

    fileInput.click();

    userInput.placeholder =
        "Upload an image and ask Jundh AI about it...";

    closeMobileSidebar();

});


// PDF ASSISTANT

pdfToolBtn.addEventListener("click", function () {

    fileInput.accept =
        "application/pdf";

    fileInput.click();

    userInput.placeholder =
        "Upload a PDF and ask a question about it...";

    closeMobileSidebar();

});


// VOICE INPUT

voiceToolBtn.addEventListener("click", function () {

    voiceBtn.click();

    closeMobileSidebar();

});


// WEB SEARCH

webToolBtn.addEventListener("click", function () {

    webSearchToggle.checked = true;

    userInput.placeholder =
        "Search the web with Jundh AI...";

    userInput.focus();

    closeMobileSidebar();

});




// CLOSE SIDEBAR ON MOBILE

function closeMobileSidebar() {

    if (window.innerWidth <= 720) {

        sidebar.classList.remove("open");

    }

}

// ========================================
// DISPLAY GENERATED IMAGE
// ========================================

function addGeneratedImage(
    message,
    imageUrl
) {

    removeWelcomeScreen();


    const row =
        document.createElement("div");

    row.className =
        "message-row ai";


    const avatar =
        document.createElement("div");

    avatar.className =
        "message-avatar";

    avatar.textContent =
        "J";


    const bubble =
        document.createElement("div");

    bubble.className =
        "message-bubble";


    const text =
        document.createElement("p");

    text.textContent =
        message ||
        "Image generated successfully.";


    const image =
        document.createElement("img");

    image.src =
        imageUrl;

    image.alt =
        "AI-generated image";

    image.className =
        "generated-image";


    bubble.appendChild(text);

    bubble.appendChild(image);

    row.appendChild(avatar);

    row.appendChild(bubble);

    chatBox.appendChild(row);


    scrollToBottom();

}


// ========================================
// CHAT HISTORY SIDEBAR
// ========================================

const chatHistoryList =
    document.getElementById("chat-history-list");

const chatSearchInput =
    document.getElementById("chat-search-input");

let savedChats = [];


// ========================================
// LOAD CHAT LIST
// ========================================

async function loadChatList() {

    try {

        const response =
            await fetch("/chats");

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        savedChats =
            data.chats || [];

        renderChatList(savedChats);

    } catch (error) {

        console.error(
            "Chat list error:",
            error
        );
    }
}


// ========================================
// DISPLAY CHAT LIST
// ========================================

function renderChatList(chats) {

    chatHistoryList.innerHTML = "";

    if (chats.length === 0) {

        chatHistoryList.innerHTML = `
            <div class="chat-history-empty">
                No saved chats yet.
            </div>
        `;

        return;
    }


    chats.forEach(function (chat) {

        const button =
            document.createElement("button");

        button.className =
            "chat-history-item";

        button.dataset.chatId =
            chat.id;


        if (
            activeChatId &&
            String(chat.id) ===
            String(activeChatId)
        ) {

            button.classList.add("active");
        }


        const icon =
            document.createElement("span");

        icon.className =
            "chat-history-icon";

        icon.textContent = "◌";


        const title =
            document.createElement("span");

        title.className =
            "chat-history-title";

        title.textContent =
            chat.title;


        // RENAME BUTTON

        const renameBtn =
            document.createElement("span");

        renameBtn.className =
            "chat-action-btn";

        renameBtn.textContent = "✏️";

        renameBtn.title =
            "Rename chat";


        renameBtn.addEventListener(
            "click",
            async function (event) {

                event.stopPropagation();

                const newTitle =
                    prompt(
                        "Rename chat:",
                        chat.title
                    );

                if (
                    !newTitle ||
                    !newTitle.trim()
                ) {
                    return;
                }


                const response =
                    await fetch(
                        `/chats/${chat.id}/rename`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                title:
                                    newTitle.trim()
                            })
                        }
                    );


                if (response.ok) {

                    await loadChatList();
                }
            }
        );


        // DELETE BUTTON

        const deleteBtn =
            document.createElement("span");

        deleteBtn.className =
            "chat-action-btn";

        deleteBtn.textContent = "🗑️";

        deleteBtn.title =
            "Delete chat";


        deleteBtn.addEventListener(
            "click",
            async function (event) {

                event.stopPropagation();

                const confirmed =
                    confirm(
                        `Delete "${chat.title}"?`
                    );

                if (!confirmed) {
                    return;
                }


                const response =
                    await fetch(
                        `/chats/${chat.id}/delete`,
                        {
                            method: "POST"
                        }
                    );


                if (response.ok) {

                    if (
                        String(activeChatId) ===
                        String(chat.id)
                    ) {

                        activeChatId = null;

                        localStorage.removeItem(
                            "jundh-active-chat-id"
                        );

                        chatBox.innerHTML = "";
                    }


                    await initializeChatHistory();
                }
            }
        );


        button.appendChild(icon);

        button.appendChild(title);

        button.appendChild(renameBtn);

        button.appendChild(deleteBtn);

        chatHistoryList.appendChild(button);

    });
}


// ========================================
// SEARCH SAVED CHATS
// ========================================

chatSearchInput.addEventListener(
    "input",
    function () {

        const searchText =
            this.value
                .trim()
                .toLowerCase();


        const filteredChats =
            savedChats.filter(
                function (chat) {

                    return chat.title
                        .toLowerCase()
                        .includes(searchText);
                }
            );


        renderChatList(filteredChats);
    }
);


// ========================================
// OPEN CHAT BY ID
// ========================================

async function openChatById(chatId) {

    try {

        const response =
            await fetch(
                `/history/${chatId}`
            );

        const data =
            await response.json();


        if (!response.ok) {

            console.error(data.error);

            return false;
        }


        activeChatId =
            String(chatId);


        chatBox.innerHTML = "";


        if (
            !data.messages ||
            data.messages.length === 0
        ) {

            addAIMessage(
                "New chat started. How can I help you?"
            );

        } else {

            data.messages.forEach(
                function (item) {

                    if (
                        item.role === "User"
                    ) {

                        addUserMessage(
                            item.message,
                            null
                        );

                    } else {

                        addAIMessage(
                            item.message
                        );
                    }
                }
            );
        }


        localStorage.setItem(
            "jundh-active-chat-id",
            activeChatId
        );


        renderChatList(savedChats);

        scrollToBottom();

        return true;


    } catch (error) {

        console.error(
            "Open chat error:",
            error
        );

        return false;
    }
}


// ========================================
// RESTORE CHAT AFTER REFRESH
// ========================================

async function initializeChatHistory() {

    await loadChatList();


    if (savedChats.length === 0) {
        return;
    }


    const storedChatId =
        localStorage.getItem(
            "jundh-active-chat-id"
        );


    const storedChatExists =
        savedChats.some(
            function (chat) {

                return (
                    String(chat.id) ===
                    String(storedChatId)
                );
            }
        );


    const chatToOpen =
        storedChatExists
            ? storedChatId
            : savedChats[0].id;


    await openChatById(chatToOpen);
}


// ========================================
// CLICK SAVED CHAT
// ========================================

chatHistoryList.addEventListener(
    "click",
    async function (event) {

        const chatButton =
            event.target.closest(
                ".chat-history-item"
            );


        if (!chatButton) {
            return;
        }


        const chatId =
            chatButton.dataset.chatId;


        await openChatById(chatId);


        if (window.innerWidth <= 720) {

            sidebar.classList.remove(
                "open"
            );
        }
    }
);


// ========================================
// START CHAT HISTORY SYSTEM
// ========================================

initializeChatHistory();