import { CloudFrontScanner, textToIps } from "./CloudFrontScanner";
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
  scanner.cdnRequest('1.1.1.2')
  expect(fetch).toBeCalledTimes(1)
  expect(fetch).toBeCalledWith('cdn-proxy.cloudfront.net', {
    headers: expect.any(Headers),
  })
  expect(fetch).toBeCalledWith('cdn-proxy.cloudfront.net', {
    headers: expect.objectContaining(new Headers({
      'Cdn-Proxy-Origin': '1.1.1.2',
      'Cdn-Proxy-Host': '1.1.1.2',
    })),
  })
});

test('calling scan does not throw an error', () => {
  let scanner = setupScanner()
  jest.spyOn(scanner, "cdnRequest").mockImplementation((backendHost: string) =>
      Promise.resolve(new Response(Readable.from('asdf')))
  );
  scanner.scan(['1.1.1.2'])
  expect(scanner.cdnRequest).toBeCalledTimes(1)
  expect(scanner.cdnRequest).toBeCalledWith('1.1.1.2')
});

test('calling textToIps with /32 results in single address', () => {
  let resp = textToIps('1.1.1.2')
  expect(resp.length).toBe(1)
  expect(resp).toContain('1.1.1.2')
});

test('calling textToIps with /24 results in 255 addresses', () => {
  let resp = textToIps('1.1.1.2/24')
  expect(resp.length).toBe(256)
  expect(resp[0]).toBe('1.1.1.0')
  expect(resp[255]).toContain('1.1.1.255')
});
