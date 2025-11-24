import React from 'react';
import './DashboredCards.css';

export interface DashboardCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  trend?: {
    value: number;
    isPositive: boolean;
  };
  onClick?: () => void;
}

export const DashboardCard: React.FC<DashboardCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  variant = 'primary',
  trend,
  onClick
}) => {
  const cardClass = `dashboard-card dashboard-card-${variant} ${onClick ? 'clickable' : ''}`;

  return (
    <div className={cardClass} onClick={onClick}>
      <div className="card-content">
        <div className="card-info">
          <h3 className="card-title">{title}</h3>
          <div className="card-value">{value}</div>
          {subtitle && <p className="card-subtitle">{subtitle}</p>}
          {trend && (
            <div className={`card-trend ${trend.isPositive ? 'positive' : 'negative'}`}>
              <span className="trend-icon">
                {trend.isPositive ? '↗' : '↘'}
              </span>
              <span className="trend-value">
                {trend.isPositive ? '+' : ''}{trend.value}%
              </span>
            </div>
          )}
        </div>
        <div className="card-icon">
          <span className="icon">{icon}</span>
        </div>
      </div>
    </div>
  );
};

export const DashboardCardsGrid: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <div className="dashboard-cards-grid">{children}</div>;
};

export default DashboardCard;