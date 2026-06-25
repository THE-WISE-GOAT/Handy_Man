const noop = () => {};

const createNoopSubscription = () => ({
  unsubscribe: noop,
  close: noop,
  disconnect: noop
});

export const connectRealtime = () => {
  return {
    isConnected: false,
    subscribeToWorkerDispatches: () => createNoopSubscription(),
    subscribeToJobUpdates: () => createNoopSubscription(),
    publishJobCreated: noop,
    publishWorkerAvailability: noop,
    disconnect: noop
  };
};

export const subscribeToWorkerDispatches = (callback) => {
  void callback;
  return createNoopSubscription();
};

export const subscribeToJobUpdates = (callback) => {
  void callback;
  return createNoopSubscription();
};

export const publishJobCreated = (payload) => {
  void payload;
};

export const publishWorkerAvailability = (payload) => {
  void payload;
};

export const disconnectRealtime = () => {};
