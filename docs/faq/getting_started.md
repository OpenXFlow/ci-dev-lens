# 🚀 Getting Started

<a name="how-to-chat"></a>
## ❓ How can I effectively chat with this project and ask questions?

To get the most accurate answers about the architecture and usage of **Agent-CI-Lens**, we recommend using a high-context LLM environment.

### Recommended Setup:
1. **Tool:** Go to [Google AI Studio (Playground)](https://aistudio.google.com/).
2. **Model:** Select a modern high-context model, such as **"Gemini X.y Flash Lite"** (or the latest preview version).
3. **Local Copy:** Clone or download the entire `agent-ci-lens` project from the github to your local disk.
4. **Context Loading:** 
   - Open the project map in `docs/ARCHITECTURE.md` to understand the layers.
   - **Upload all files (py,md,..)** from the project (or relevant directories like `.agents,.claude,.devcontainer,agent_context,agent_core,agent_tests` and files in rootdirectory  into the AI Studio prompt window.
5. **Start Questioning:** Once the files are uploaded, the AI has "Full Vision" of the codebase.

### Suggested Questions to Start With:
##### Basic questions
- *"Explain the state transition from STRATEGY to EXECUTING."*
- *"How can I add a new skill to the orchestrator?"*
- *"Summarize the current project standards in pyproject.toml."*
- *"What are the safety mechanisms preventing the AI from deleting my tasks?"*

##### Diagrams
- *"Generate a Mermaid diagram showing the flow of data between SessionManager and the LLM API Client."**
- *"Based on the engine.py logic, create a Mermaid sequence diagram for a failed VCS_DELIVERY attempt."**

##### Tip for Visualization:
When you ask Gemini to generate diagrams, always specify: *"Provide the result in Mermaid.js syntax."* You can then copy this code and paste it into any Mermaid live editor or view it directly in VS Code to see the updated architectural flow.