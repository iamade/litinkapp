import React from 'react';

type ProtectedImageProps = React.ImgHTMLAttributes<HTMLImageElement>;

const ProtectedImage: React.FC<ProtectedImageProps> = ({
  onContextMenu,
  onDragStart,
  style,
  ...props
}) => {
  return (
    <img
      {...props}
      onContextMenu={(event) => {
        event.preventDefault();
        onContextMenu?.(event);
      }}
      onDragStart={(event) => {
        event.preventDefault();
        onDragStart?.(event);
      }}
      style={{
        userSelect: 'none',
        WebkitUserDrag: 'none',
        ...style,
      } as React.CSSProperties}
    />
  );
};

export default ProtectedImage;
