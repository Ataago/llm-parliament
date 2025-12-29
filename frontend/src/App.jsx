import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import './App.css';

function App() {
    const [conversations, setConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [currentConversation, setCurrentConversation] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    // Debate Configuration State
    const [debateConfig, setDebateConfig] = useState({
        pro_model: "anthropic/claude-sonnet-4.5",
        con_model: "openai/gpt-4o-mini",
        moderator_model: "google/gemini-2.5-flash",
        max_rounds: 3,
        enable_tools: true,
    });

    // Load conversations on mount
    useEffect(() => {
        loadConversations();
    }, []);

    // Load conversation details when selected
    useEffect(() => {
        if (currentConversationId) {
            loadConversation(currentConversationId);
        }
    }, [currentConversationId]);

    const loadConversations = async () => {
        try {
            const convs = await api.listConversations();
            setConversations(convs);
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    };

    const loadConversation = async (id) => {
        try {
            const conv = await api.getConversation(id);
            setCurrentConversation(conv);
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    };

    const handleNewConversation = async () => {
        try {
            const newConv = await api.createConversation();
            setConversations([
                { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
                ...conversations,
            ]);
            setCurrentConversationId(newConv.id);
            // Reset config for new debate? Or keep user settings? 
            // Keeping settings is usually better UX.
        } catch (error) {
            console.error('Failed to create conversation:', error);
        }
    };

    const handleSelectConversation = (id) => {
        setCurrentConversationId(id);
    };

    const handleSendMessage = async (content) => {
        if (!currentConversationId) return;

        setIsLoading(true);
        try {
            // 1. Optimistically add USER message
            const userMessage = { role: 'user', content };
            setCurrentConversation((prev) => ({
                ...prev,
                messages: [...prev.messages, userMessage],
            }));

            // 2. Stream Response
            await api.sendMessageStream(
                currentConversationId,
                content,
                debateConfig, // Pass the current config here
                (eventType, event) => {

                    if (eventType === 'message') {
                        setCurrentConversation((prev) => {
                            const newMsg = event.data;
                            // Check if the last message is from the SAME speaker and has tool logs
                            // If so, we might want to "finalize" that message content instead of appending
                            // BUT, typically the "final answer" comes as a separate chunk from the "tool call" chunk.
                            // We should append or update.

                            const lastMsg = prev.messages[prev.messages.length - 1];

                            // If last message was a "Thinking" state (empty content + tools) from same person
                            if (lastMsg && lastMsg.name === newMsg.name && lastMsg.isThinking) {
                                // Update the existing message with final content
                                const updatedMsgs = [...prev.messages];
                                updatedMsgs[updatedMsgs.length - 1] = {
                                    ...lastMsg,
                                    content: newMsg.content,
                                    isThinking: false
                                };
                                return { ...prev, messages: updatedMsgs };
                            }

                            // Normal append (or de-dupe)
                            const exists = prev.messages.some(m =>
                                m.role === newMsg.role &&
                                m.name === newMsg.name &&
                                m.content === newMsg.content
                            );
                            if (exists) return prev;
                            return { ...prev, messages: [...prev.messages, newMsg] };
                        });

                    } else if (eventType === 'tool_call') {
                        // Agent is calling a tool. Create/Update message with "Thinking" state
                        setCurrentConversation((prev) => {
                            const toolMsg = event.data;
                            const lastMsg = prev.messages[prev.messages.length - 1];

                            // If we already have a message from this agent, append tool call
                            if (lastMsg && lastMsg.name === toolMsg.name) {
                                const updatedMsgs = [...prev.messages];
                                updatedMsgs[updatedMsgs.length - 1] = {
                                    ...lastMsg,
                                    tool_calls: [...(lastMsg.tool_calls || []), ...(toolMsg.tool_calls || [])],
                                    isThinking: true // Mark as thinking/processing
                                };
                                return { ...prev, messages: updatedMsgs };
                            }

                            // Else create new "Thinking" message
                            const newMsg = {
                                ...toolMsg,
                                content: "🤔 Analyzing...", // Fallback text
                                messages: [], // Ensure tools array exists
                                isThinking: true
                            };
                            return { ...prev, messages: [...prev.messages, newMsg] };
                        });

                    } else if (eventType === 'tool_output') {
                        // Attach output to the last message (which should be the one that called it)
                        setCurrentConversation((prev) => {
                            const toolOutput = event.data;
                            const lastMsg = prev.messages[prev.messages.length - 1];

                            if (lastMsg) {
                                const updatedMsgs = [...prev.messages];
                                // Add to a 'tool_outputs' array
                                updatedMsgs[updatedMsgs.length - 1] = {
                                    ...lastMsg,
                                    tool_outputs: [...(lastMsg.tool_outputs || []), toolOutput]
                                };
                                return { ...prev, messages: updatedMsgs };
                            }
                            return prev;
                        });

                    } else if (eventType === 'status') {
                        // Optional: Display moderator status updates (decisions) in UI
                        console.log("Status update:", event.data);
                    } else if (eventType === 'title') {
                        loadConversations(); // Refresh list to show new title
                    } else if (eventType === 'complete') {
                        setIsLoading(false);
                    } else if (eventType === 'error') {
                        console.error('Stream error:', event.message);
                        setIsLoading(false);
                    }
                });
        } catch (error) {
            console.error('Failed to send message:', error);
            setIsLoading(false);
        }
    };

    return (
        <div className="app">
            <Sidebar
                conversations={conversations}
                currentConversationId={currentConversationId}
                onSelectConversation={handleSelectConversation}
                onNewConversation={handleNewConversation}
                config={debateConfig}
                onConfigChange={setDebateConfig}
            />
            <ChatInterface
                conversation={currentConversation}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
            />
        </div>
    );
}

export default App;