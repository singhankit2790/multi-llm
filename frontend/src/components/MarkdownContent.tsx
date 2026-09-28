import Markdown from "react-markdown";

type MarkdownContentProps = {
  text: string;
};

export function MarkdownContent({ text }: MarkdownContentProps) {
  return (
    <div className="markdown-body text-[0.9375rem] leading-7 text-zinc-200">
      <Markdown
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {text}
      </Markdown>
    </div>
  );
}
