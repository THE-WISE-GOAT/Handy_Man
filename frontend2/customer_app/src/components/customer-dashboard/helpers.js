import { TAG_LIBRARY } from './constants';

const TAG_MAP = [
  { match: /plumb|pipe|drain|leak|faucet|toilet/i, tag: 'Plumber' },
  { match: /electric|power|wire|socket|light|fuse|switch/i, tag: 'Electrician' },
  { match: /solar|panel|inverter|battery/i, tag: 'SolarTech' },
  { match: /ac|air ?condition|hvac|cooling|heating/i, tag: 'HVAC' },
  { match: /fridge|washing machine|microwave|oven|appliance/i, tag: 'Appliance Repair' },
  { match: /wood|door|cabinet|furniture|carpenter/i, tag: 'Carpenter' },
  { match: /urgent|emergency|immediately|asap|danger|sparking/i, tag: 'Emergency' }
];

export function extractTagsFromText(text = '') {
  const detected = TAG_MAP.filter((item) => item.match.test(text)).map((item) => item.tag);
  return TAG_LIBRARY.filter((tag) => detected.includes(tag));
}

export function mergeUniqueTags(currentTags = [], incomingTags = []) {
  return Array.from(new Set([...(currentTags || []), ...(incomingTags || [])]));
}

export function formatTimestamp(value) {
  if (!value) return 'Just now';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Just now';
  return date.toLocaleString();
}

export function buildChatHistory(messages = []) {
  return messages.map((message, index) => ({
    id: message.id || `msg-${index}`,
    sender: message.sender === 'user' ? 'user' : 'ai',
    text: message.message || message.text || '',
    timestamp: formatTimestamp(message.timestamp)
  }));
}

export function normalizeTask(task) {
  return {
    id: task.id,
    title: task.problem_description || 'Untitled request',
    status: task.status || 'open',
    description: task.problem_description || '',
    createdAt: task.created_at || null,
    assignedWorker: task.assigned_worker || 'Awaiting assignment',
    amount: task.amount || null,
    eta: task.eta || 'Pending dispatch'
  };
}

export function deriveBiddings(tasks = []) {
  return tasks
    .filter((task) => ['matched', 'open'].includes(task.status))
    .map((task) => ({
      id: task.id,
      title: task.problem_description || 'Service request',
      status: task.status || 'open',
      worker: task.assigned_worker || 'Bids pending',
      amount: task.amount ? `रू ${task.amount}` : 'Awaiting quote',
      submittedAt: formatTimestamp(task.created_at)
    }));
}

export function deriveHistory(tasks = []) {
  return tasks
    .filter((task) => task.status === 'completed')
    .map((task) => ({
      id: task.id,
      date: formatTimestamp(task.created_at),
      serviceType: task.problem_description || 'Service request',
      providerName: task.assigned_worker || 'Assigned worker unavailable',
      cost: task.amount ? `रू ${task.amount}` : 'N/A'
    }));
}
