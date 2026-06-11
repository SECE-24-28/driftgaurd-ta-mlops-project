import React from 'react';
import { Toaster } from 'react-hot-toast';
import '../styles/globals.css';

export default function App({ Component, pageProps }) {
  return (
    <>
      <Component {...pageProps} />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1c2128',
            color: '#e6edf3',
            border: '1px solid #30363d',
            fontSize: '13px',
            borderRadius: '8px',
            padding: '12px 16px'
          },
        }}
      />
    </>
  );
}
