const KEY = 'nav_back_stack';
const MAX = 30;

const read = () => {
  try { return JSON.parse(sessionStorage.getItem(KEY)) || []; } catch { return []; }
};

const write = (stack) => {
  try { sessionStorage.setItem(KEY, JSON.stringify(stack.slice(-MAX))); } catch { /* quota */ }
};

export const recordVisit = (fullPath) => {
  const stack = read();
  if (stack[stack.length - 1] === fullPath) return;
  const i = stack.indexOf(fullPath);
  if (i !== -1) stack.splice(i, 1);
  stack.push(fullPath);
  write(stack);
};

export const popPrevious = (currentPath) => {
  const stack = read();
  while (stack.length && (stack[stack.length - 1] === currentPath
    || stack[stack.length - 1].split('?')[0] === currentPath.split('?')[0])) stack.pop();
  const prev = stack.pop() || null;
  write(stack);
  return prev;
};
