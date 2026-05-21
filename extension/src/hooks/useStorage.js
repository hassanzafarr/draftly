import { useState, useEffect } from 'react';

export function useStorage(key, defaultValue, area = 'sync') {
  const [value, setValue] = useState(defaultValue);

  useEffect(() => {
    const storage = area === 'local' ? chrome.storage.local : chrome.storage.sync;
    storage.get(key).then(result => {
      if (result[key] !== undefined) setValue(result[key]);
    });

    const listener = (changes, changedArea) => {
      if (changedArea === area && changes[key] !== undefined) {
        setValue(changes[key].newValue ?? defaultValue);
      }
    };
    chrome.storage.onChanged.addListener(listener);
    return () => chrome.storage.onChanged.removeListener(listener);
  }, [key, area]);

  function persist(newValue) {
    const storage = area === 'local' ? chrome.storage.local : chrome.storage.sync;
    storage.set({ [key]: newValue });
    setValue(newValue);
  }

  return [value, persist];
}
