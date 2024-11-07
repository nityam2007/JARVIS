# Jarvis AI Assistant

## \*\*IN DEVELOPMENT

Jarvis AI Assistant is a powerful virtual assistant that can help you with various tasks such as controlling applications, managing system operations, playing music, and more. It utilizes voice recognition and can interact with you intelligently using the Llama3-8B-8192 AI model.

## 📚 Documentation

The documentation for Jarvis is organized into several sections for easier navigation. Please refer to the following:

### [User Manual - Master JARVIS](docs/user_manual.md)

A complete guide on how to use Jarvis, from setting up voice recognition to executing commands.

### [Installation - Deploy your Assistant](docs/installation.md)

Step-by-step instructions on how to install and set up Jarvis on your machine.

### [Command Index - All Capabilities](docs/command_index.md)

A comprehensive list of all voice commands Jarvis can recognize and execute.

### [Technical Specs - Under the Hood](docs/technical_specs.md)

Detailed explanation of how Jarvis works internally, including the AI model, system requirements, and integration specifics.

### [Development - Enhance JARVIS](docs/development.md)

For developers who want to contribute or extend Jarvis with custom features and functionality.

### [Troubleshooting - Issue Resolution](docs/troubleshooting.md)

Solutions to common issues you may encounter while using Jarvis, including installation and runtime errors.

## Features

- **Voice Recognition**: Responds to custom wake words, listens for commands, and can handle context-aware conversations.
- **Application Control**: Launch and control browsers, media players, productivity tools, and system utilities.
- **Music Playback**: Control media playback on Spotify and other integrated media tools.
- **System Control**: Perform system operations like shutdown, restart, and sleep commands.
- **AI-Powered Responses**: Contextual and intelligent responses powered by the Llama3-8B-8192 model.
- **Customizable**: Tailor Jarvis’s behavior through a configurable JSON file and easy-to-use settings.

## Installation

Follow the steps below to set up **Jarvis AI Assistant** on your system.

### 1. Install Python

Ensure Python 3.8 or higher is installed on your machine. Download it from the official [Python website](https://www.python.org/downloads/).

### 2. Clone the Repository

Clone the Jarvis repository to your local machine:

```bash
git clone https://github.com/your-repository/jarvis-ai-assistant.git
cd jarvis-ai-assistant
```

### 3. Install Dependencies

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

### 4. Configuration

Customize Jarvis by editing the `config.json` file:

- **Voice Settings**: Adjust wake words, recognition sensitivity, and voice properties.
- **Command Settings**: Configure commands and system control options.
- **AI Model**: Adjust AI response behavior, including temperature and token limits.

Example `config.json`: [config.json](config.json)

### 5. Set Up Environment Variables

Create a `.env` file in the root directory of your project, and add the following line:

```env
GROQ_API_KEY=<yourkey>
```

This key is necessary to connect Jarvis with the Groq API.

Example `.env` file:

```env
# .env.example
GROQ_API_KEY=your-api-key-here
```

Rename this file to `.env` after setting your API key.

### 6. Run Jarvis

Once configured, you can run the Jarvis AI Assistant by executing the `main.py` file:

```bash
python main.py
```

Jarvis will begin listening for your wake word and will be ready to execute commands.

---

## Usage

Here are a few example commands you can say to Jarvis:

- "Hey Jarvis, open Chrome."
- "Jarvis, play my Spotify playlist."
- "Shutdown the system."
- "What’s the weather like today?"
- "Play some relaxing music."

For a full list of available commands, see the [Command Index](docs/command_index.md).

---

## Contributing

Jarvis is an open-source project, and contributions are welcome! If you want to improve Jarvis or add new features, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Implement your changes.
4. Submit a pull request with a detailed description of your modifications.

---

## License

This project is licensed under the **Apache License 2.0**.

---

## Troubleshooting

If you encounter any issues, please refer to the [Troubleshooting](docs/troubleshooting.md) section for help with common errors, installation problems, and runtime issues.

---

Thank you for using **Jarvis AI Assistant**! 🎉

---

## 📝 Notes

For detailed and advanced configurations, please refer to the respective documentation files located in the `docs/` folder.
