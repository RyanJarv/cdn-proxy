import { CloudFrontScanner } from "./CloudFrontScanner";
const Readable = require('stream').Readable;

function setupScanner(): CloudFrontScanner {
  return new CloudFrontScanner('cdn-proxy.cloudfront.net')
}

test('scanner init sets values correctly', () => {
  let scanner = setupScanner()
  expect(scanner.cdnProxy === 'cdn-proxy.cloudfront.net')
  expect(scanner.hostnames === [])
});

test('calling request does not throw an error', () => {
  let scanner = setupScanner()
  jest.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve(new Response(Readable.from('asdf')))
  );
  scanner.request('1.1.1.1')
  expect(fetch).toBeCalledTimes(1)
  expect(fetch).toBeCalledWith('cdn-proxy.cloudfront.net', {
    headers: expect.any(Headers),
  })
  expect(fetch).toBeCalledWith('cdn-proxy.cloudfront.net', {
    headers: expect.objectContaining(new Headers({
      'Cdn-Proxy-Origin': '1.1.1.1',
      'Cdn-Proxy-Host': '1.1.1.1',
    })),
  })
});

test('calling scan does not throw an error', () => {
  let scanner = setupScanner()
  jest.spyOn(scanner, "request").mockImplementation((backendHost: string) =>
      Promise.resolve(new Response(Readable.from('asdf')))
  );
  scanner.scan(['1.1.1.1'])
  expect(scanner.request).toBeCalledTimes(1)
  expect(scanner.request).toBeCalledWith('1.1.1.1')
});
