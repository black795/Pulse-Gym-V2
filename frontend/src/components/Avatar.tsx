interface AvatarProps {
  name: string;
  photo?: string | null;
  size?: number;
  color?: string;
}

export default function Avatar({ name, photo, size = 36, color }: AvatarProps) {
  const initial = name.charAt(0).toUpperCase();

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
        background: color ? color + '22' : 'var(--primary-tint)',
        border: `1.5px solid ${color ? color + '44' : 'var(--border)'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        fontFamily: 'var(--font-sora)',
        fontWeight: 700,
        fontSize: size * 0.38,
        color: color || 'var(--primary)',
      }}
    >
      {initial}
    </div>
  );
}
