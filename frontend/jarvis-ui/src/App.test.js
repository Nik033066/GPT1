import { render, screen } from "@testing-library/react";

jest.useFakeTimers();

jest.mock("react-markdown", () => {
  return function ReactMarkdownMock(props) {
    return props.children;
  };
});

jest.mock("axios", () => {
  return {
    __esModule: true,
    default: {
      get: jest.fn(),
      post: jest.fn(),
      create: jest.fn(function create() {
        return {
          get: jest.fn(),
          post: jest.fn(),
        };
      }),
    },
  };
});

const App = require("./App").default;
const { ThemeProvider } = require("./contexts/ThemeContext");

test("renders app title", () => {
  render(
    <ThemeProvider>
      <App />
    </ThemeProvider>
  );
  expect(screen.getByText(/Agentic Local/i)).toBeInTheDocument();
});
