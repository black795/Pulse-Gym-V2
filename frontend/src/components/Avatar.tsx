interface AvatarProps {
  name: string;
  photo?: string | null;
  size?: number;
  color?: string;
}

export default function Avatar({ name, photo, size = 36, color }: AvatarProps) {
  const initial = name.charAt(0).toUpperCase();
  const bg = color || '#16A34A';

  if (photo) {
    return (
      <img
        src={photo}
        alt={name}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          objectFit: 'cover',
          flexShrink: 0,
        }}
      />
    );
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: bg + '22',
        border: `1.5px solid ${bg}44`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        fontFamily: 'var(--font-sora)',
        fontWeight: 700,
        fontSize: size * 0.38,
        color: bg,
      }}
    >
      {initial}
    </div>
  );
}
