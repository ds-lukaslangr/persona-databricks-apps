import { useState } from 'react';
import {
  Paper,
  TextInput,
  Group,
  Stack,
  Text,
  ScrollArea,
  Box,
  ActionIcon,
  Code,
} from '@mantine/core';
import { IconSend, IconRobot } from '@tabler/icons-react';
import axios from 'axios';

function SQLQueryMessage({ sql }) {
  return (
    <Code block style={{ 
      whiteSpace: 'pre-wrap',
      backgroundColor: '#f8f9fa',
      padding: '1rem',
      borderRadius: '4px',
      fontSize: '0.9em',
      maxHeight: '200px',
      overflowY: 'auto'
    }}>
      {sql}
    </Code>
  );
}

export function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    // Add user message to chat
    setMessages(prev => [...prev, { text: userMessage, isUser: true }]);

    try {
      const response = await axios.post('/api/chat', { message: userMessage });

      // Add attachments as separate messages
      if (response.data.attachments) {
        response.data.attachments.forEach(attachment => {
          let messageContent;
          if (attachment.type === 'text') {
            messageContent = { text: attachment.content, isUser: false };
          } else if (attachment.type === 'query') {
            messageContent = { 
              sql: attachment.sql, 
              status: attachment.status,
              isUser: false,
              isQuery: true
            };
          }
          if (messageContent) {
            setMessages(prev => [...prev, messageContent]);
          }
        });
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        text: 'Sorry, I encountered an error. Please try again.', 
        isUser: false 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Paper shadow="sm" radius="md" p="md" style={{ height: '500px', display: 'flex', flexDirection: 'column' }}>
      <ScrollArea style={{ flex: 1 }} mb="md">
        <Stack spacing="md">
          {messages.map((message, index) => (
            <Box
              key={index}
              style={{
                alignSelf: message.isUser ? 'flex-end' : 'flex-start',
                maxWidth: '80%',
              }}
            >
              <Paper
                p="sm"
                radius="md"
                bg={message.isUser ? 'blue.5' : 'gray.1'}
                style={{
                  color: message.isUser ? 'white' : 'inherit',
                }}
              >
                {message.isQuery ? (
                  <SQLQueryMessage sql={message.sql} />
                ) : (
                  <Text>{message.text}</Text>
                )}
              </Paper>
            </Box>
          ))}
        </Stack>
      </ScrollArea>

      <Group spacing="xs">
        <TextInput
          placeholder="Ask about your data..."
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          onKeyPress={handleKeyPress}
          style={{ flex: 1 }}
          icon={<IconRobot size={18} />}
          disabled={isLoading}
        />
        <ActionIcon
          size="lg"
          color="blue"
          variant="filled"
          onClick={sendMessage}
          loading={isLoading}
          disabled={!input.trim()}
        >
          <IconSend size={18} />
        </ActionIcon>
      </Group>
    </Paper>
  );
}