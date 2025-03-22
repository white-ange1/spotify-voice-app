const startButton = document.getElementById("startListening");
const mic_status = document.getElementById("mic_status");

// Checks for browser support
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

if (!SpeechRecognition) {
    mic_status.textContent = "speech recognition not supported.";
    console.error("Speech Recognition not supported.");
} else {
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false; // stops after a single voice command
    recognition.interimResults = false; // only process final results

    // Start listening on button click
    startButton.addEventListener("click", () => {
        recognition.start();
        startButton.disabled = true;
        mic_status.textContent = "🎤 Listening...";
        console.log("Listening started...")
    });

    // Handle recognition result
    recognition.onresult = (event) => {
        const command = event.results[0][0].transcript.toLowerCase();
        console.log("Recognized Command:", command);
        mic_status.textContent = `🗣 Your Command: "${command}"`;

        // Send recognized command to Flask backend
        fetch("/voice_control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({command}),
        })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then((data) => {
            console.log("ServerResponse:", data);
            mic_status.textContent = data.message || "Command sent.";
        })
        .catch((error) => {
            console.error("Error sending command:", error);
            mic_status.textContent = "Error sending command:" + error.message;
        });
    };    

    // Handle recognition errors
    recognition.onerror = (event) => {
        console.error("Recognition Error:  ", event.error);
        mic_status.textContent = "Recognition error." + event.error;
        startButton.disabled = false;
    };

    // Reset status when listening stops
    recognition.onend = () => {
        startButton.disabled = false;
        console.log("Listening stopped.");
    };
}