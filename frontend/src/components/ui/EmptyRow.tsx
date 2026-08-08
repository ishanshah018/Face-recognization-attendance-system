interface EmptyRowProps {
  columns: number;
  text: string;
}

export function EmptyRow({ columns, text }: EmptyRowProps) {
  return (
    <tr>
      <td colSpan={columns} className="empty-cell">
        {text}
      </td>
    </tr>
  );
}
