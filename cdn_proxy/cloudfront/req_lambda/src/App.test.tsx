import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders home react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/home/i);
  expect(linkElement).toBeInTheDocument();
});

test('renders scanner react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/scanner/i);
  expect(linkElement).toBeInTheDocument();
});
