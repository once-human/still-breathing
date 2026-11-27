/** made fresh for each page you open, so its parts rise in (globals.css, .a-page) */
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="a-page">{children}</div>;
}
