import { Plus, Settings, Send, Mic, MessageCircle, ArrowLeft, ArrowRight, Webhook} from 'lucide-react';

const icons = {
  plus: Plus,
  settings: Settings,
  send: ArrowRight,
  mic: Mic,
  message: MessageCircle,
  arrowLeft: ArrowLeft,
  webhook: Webhook,
};

export default function Icon({ name, size = 20, className = '' }) {
  const LucideIcon = icons[name];

  if (!LucideIcon) {
    console.warn(`Иконка "${name}" не найдена в Icon.jsx`);
    return null;
  }

  return (
    <LucideIcon
      className={className}
      size={size}
      strokeWidth={1.7}
      aria-hidden="true"
    />
  );
}