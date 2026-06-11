import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en" className="dark">
      <Head>
        <meta charSet="utf-8" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <body className="bg-[#0d1117] text-[#e6edf3]">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
