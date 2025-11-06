import axios, { AxiosInstance } from 'axios';
import { ChatRequest, ChatResponse } from './types';
import { API_URL } from './constants';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  try {
    const response = await apiClient.post<ChatResponse>('/chat', request);
    return response.data;
  } catch (error) {
    console.error('Chat API error:', error);
    throw error;
  }
}

export async function healthCheck(): Promise<void> {
  try {
    await apiClient.get('/health');
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
}
