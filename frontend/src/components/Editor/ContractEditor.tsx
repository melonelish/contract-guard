import { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Placeholder from '@tiptap/extension-placeholder';
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  OrderedListOutlined,
  UnorderedListOutlined,
  AlignLeftOutlined,
  AlignCenterOutlined,
  AlignRightOutlined,
  UndoOutlined,
  RedoOutlined,
} from '@ant-design/icons';
import { Button, Space } from 'antd';

interface ContractEditorProps {
  content: string;
  onChange?: (content: string) => void;
  editable?: boolean;
  placeholder?: string;
}

export function ContractEditor({
  content,
  onChange,
  editable = true,
  placeholder = '在此整理审查建议内容...',
}: ContractEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        underline: false,
      }),
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getHTML());
    },
    editorProps: {
      attributes: {
        style: 'outline: none;',
      },
    },
  });

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  if (!editor) {
    return null;
  }

  return (
    <div
      style={{
        border: '1px solid var(--line)',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--surface-strong)',
        overflow: 'hidden',
      }}
    >
      {editable && (
        <div
          style={{
            borderBottom: '1px solid var(--line)',
            padding: '10px 14px',
            background: 'var(--surface-soft)',
            display: 'flex',
            gap: 8,
            flexWrap: 'wrap',
          }}
        >
          <Space.Compact>
            <Button
              size="small"
              icon={<BoldOutlined />}
              type={editor.isActive('bold') ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().toggleBold().run()}
              title="加粗"
            />
            <Button
              size="small"
              icon={<ItalicOutlined />}
              type={editor.isActive('italic') ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().toggleItalic().run()}
              title="斜体"
            />
            <Button
              size="small"
              icon={<UnderlineOutlined />}
              type={editor.isActive('underline') ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              title="下划线"
            />
          </Space.Compact>

          <Space.Compact>
            <Button
              size="small"
              icon={<OrderedListOutlined />}
              type={editor.isActive('orderedList') ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              title="有序列表"
            />
            <Button
              size="small"
              icon={<UnorderedListOutlined />}
              type={editor.isActive('bulletList') ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              title="无序列表"
            />
          </Space.Compact>

          <Space.Compact>
            <Button
              size="small"
              icon={<AlignLeftOutlined />}
              type={editor.isActive({ textAlign: 'left' }) ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().setTextAlign('left').run()}
              title="左对齐"
            />
            <Button
              size="small"
              icon={<AlignCenterOutlined />}
              type={editor.isActive({ textAlign: 'center' }) ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().setTextAlign('center').run()}
              title="居中"
            />
            <Button
              size="small"
              icon={<AlignRightOutlined />}
              type={editor.isActive({ textAlign: 'right' }) ? 'primary' : 'default'}
              onClick={() => editor.chain().focus().setTextAlign('right').run()}
              title="右对齐"
            />
          </Space.Compact>

          <Space.Compact>
            <Button
              size="small"
              icon={<UndoOutlined />}
              onClick={() => editor.chain().focus().undo().run()}
              disabled={!editor.can().undo()}
              title="撤销"
            />
            <Button
              size="small"
              icon={<RedoOutlined />}
              onClick={() => editor.chain().focus().redo().run()}
              disabled={!editor.can().redo()}
              title="重做"
            />
          </Space.Compact>
        </div>
      )}

      <div
        style={{
          padding: '20px 24px',
          minHeight: editable ? 400 : 200,
          maxHeight: 600,
          overflowY: 'auto',
          fontFamily: 'var(--font-serif)',
          fontSize: 15,
          lineHeight: 1.9,
          color: 'var(--ink)',
        }}
      >
        <EditorContent editor={editor} />
      </div>

      <style>{`
        .ProseMirror {
          outline: none;
        }
        .ProseMirror p.is-editor-empty:first-child::before {
          content: attr(data-placeholder);
          float: left;
          color: var(--ink-muted);
          pointer-events: none;
          height: 0;
        }
        .ProseMirror h1 {
          font-size: 24px;
          font-weight: 700;
          margin: 20px 0 12px;
        }
        .ProseMirror h2 {
          font-size: 20px;
          font-weight: 600;
          margin: 18px 0 10px;
        }
        .ProseMirror h3 {
          font-size: 17px;
          font-weight: 600;
          margin: 16px 0 8px;
        }
        .ProseMirror p {
          margin: 12px 0;
        }
        .ProseMirror ul,
        .ProseMirror ol {
          padding-left: 24px;
          margin: 12px 0;
        }
        .ProseMirror li {
          margin: 6px 0;
        }
        .ProseMirror strong {
          font-weight: 700;
        }
        .ProseMirror em {
          font-style: italic;
        }
        .ProseMirror u {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
}
