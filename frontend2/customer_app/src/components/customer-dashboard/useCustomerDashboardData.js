import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient, normalizeApiError } from '@shared/api/client';
import { CHAT_FALLBACK_OPENING } from './constants';
import {
  buildChatHistory,
  deriveBiddings,
  deriveHistory,
  extractTagsFromText,
  mergeUniqueTags,
  normalizeTask
} from './helpers';

export function useCustomerDashboardData(user) {
  const [chatMessages, setChatMessages] = useState([CHAT_FALLBACK_OPENING]);
  const [chatInput, setChatInput] = useState('');
  const [activeTags, setActiveTags] = useState([]);
  const [workersAround, setWorkersAround] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState({ tasks: false, workers: false, chat: false, history: false });
  const [errors, setErrors] = useState({ tasks: '', workers: '', chat: '' });
  const [workerApplicationStatus, setWorkerApplicationStatus] = useState('');

  const location = useMemo(() => ({ lat: 27.7172, lng: 85.324 }), []);

  const loadTasks = useCallback(async () => {
    if (!user) return;
    setLoading((prev) => ({ ...prev, tasks: true, history: true }));
    setErrors((prev) => ({ ...prev, tasks: '' }));

    try {
      const result = await apiClient.get('/service-tasks/');
      setTasks(Array.isArray(result) ? result.map(normalizeTask) : []);
    } catch (error) {
      const normalized = normalizeApiError(error, 'Could not load tasks.');
      setErrors((prev) => ({ ...prev, tasks: normalized.message }));
    } finally {
      setLoading((prev) => ({ ...prev, tasks: false, history: false }));
    }
  }, [user]);

  const loadChatHistory = useCallback(async () => {
    if (!user) return;
    try {
      const result = await apiClient.get('/chat/history');
      const history = buildChatHistory(Array.isArray(result) ? result : []);
      if (history.length > 0) {
        setChatMessages(history);
        setActiveTags(history.reduce((acc, item) => mergeUniqueTags(acc, extractTagsFromText(item.text)), []));
      }
    } catch {
      // Keep dashboard resilient if history is unavailable.
    }
  }, [user]);

  const loadWorkersAround = useCallback(async () => {
    if (!user) return;
    setLoading((prev) => ({ ...prev, workers: true }));
    setErrors((prev) => ({ ...prev, workers: '' }));

    try {
      const search = new URLSearchParams({
        lat: String(location.lat),
        lng: String(location.lng),
        radius_km: '10'
      });
      const result = await apiClient.get(`/service-tasks/available-workers?${search.toString()}`);
      setWorkersAround(Array.isArray(result) ? result : []);
    } catch (error) {
      const normalized = normalizeApiError(error, 'Could not load nearby workers.');
      setErrors((prev) => ({ ...prev, workers: normalized.message }));
    } finally {
      setLoading((prev) => ({ ...prev, workers: false }));
    }
  }, [location.lat, location.lng, user]);

  useEffect(() => {
    loadTasks();
    loadChatHistory();
    loadWorkersAround();
  }, [loadChatHistory, loadTasks, loadWorkersAround]);

  const sendChatMessage = useCallback(async () => {
    const message = chatInput.trim();
    if (!message || !user) return;

    const optimisticUserMessage = {
      id: `local-${Date.now()}`,
      sender: 'user',
      text: message,
      timestamp: 'Just now'
    };

    setChatMessages((prev) => [...prev, optimisticUserMessage]);
    setActiveTags((prev) => mergeUniqueTags(prev, extractTagsFromText(message)));
    setChatInput('');
    setLoading((prev) => ({ ...prev, chat: true }));
    setErrors((prev) => ({ ...prev, chat: '' }));

    try {
      const response = await apiClient.post('/chat/message', { message });
      const aiText = response?.response || 'Diagnostic logged. Dispatch review queued.';
      setChatMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: aiText,
          timestamp: 'Just now'
        }
      ]);
      setActiveTags((prev) => mergeUniqueTags(prev, extractTagsFromText(`${message} ${aiText}`)));
      await loadTasks();
    } catch (error) {
      const normalized = normalizeApiError(error, 'Could not send message.');
      setErrors((prev) => ({ ...prev, chat: normalized.message }));
      setChatMessages((prev) => [
        ...prev,
        {
          id: `ai-fallback-${Date.now()}`,
          sender: 'ai',
          text: 'Diagnostic logged. I have pinned appropriate categorization markers onto your tracking dashboard configuration panel.',
          timestamp: 'Just now'
        }
      ]);
    } finally {
      setLoading((prev) => ({ ...prev, chat: false }));
    }
  }, [chatInput, loadTasks, user]);

  const applyForWorkerRole = useCallback(async () => {
    try {
      const response = await apiClient.post('/workers/apply', {});
      setWorkerApplicationStatus(response?.message || 'Worker role activated successfully');
    } catch (error) {
      const normalized = normalizeApiError(error, 'Failed to apply for worker role.');
      setWorkerApplicationStatus(normalized.message);
    }
  }, []);

  const activeTask = useMemo(
    () => tasks.find((task) => ['open', 'matched'].includes(task.status)) || null,
    [tasks]
  );

  const biddings = useMemo(() => deriveBiddings(tasks), [tasks]);
  const history = useMemo(() => deriveHistory(tasks), [tasks]);

  return {
    location,
    chatMessages,
    chatInput,
    setChatInput,
    sendChatMessage,
    activeTags,
    workersAround,
    tasks,
    activeTask,
    biddings,
    history,
    loading,
    errors,
    workerApplicationStatus,
    applyForWorkerRole,
    refreshWorkers: loadWorkersAround,
    refreshTasks: loadTasks
  };
}
