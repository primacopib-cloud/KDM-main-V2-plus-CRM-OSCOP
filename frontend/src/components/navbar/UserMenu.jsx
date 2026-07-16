import React from 'react';
import { Link } from 'react-router-dom';
import {
  User, LogOut, Settings, Shield, LayoutDashboard, ShoppingCart, Package,
  FileText, Wallet, Users, BarChart3, Store, Building2, ChevronDown, Bell,
  FileSignature, MapPin, CreditCard, Home, Heart, Truck, HeartHandshake, Server,
} from 'lucide-react';

export const UserMenu = ({ user, showUserMenu, setShowUserMenu, handleLogout }) => (
                <div className="relative">
                  <button 
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/[0.06] transition-colors"
                  >
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#D9B35A] to-[#D4AF37] flex items-center justify-center">
                      <User className="w-3.5 h-3.5 text-black" />
                    </div>
                    <span className="text-sm text-white/90 hidden md:block max-w-[120px] truncate">
                      {user?.contact_name || user?.email?.split('@')[0] || 'Mon compte'}
                    </span>
                    <ChevronDown className="w-3.5 h-3.5 text-white/50" />
                  </button>

                  {showUserMenu && (
                    <div 
                      className="absolute right-0 mt-2 w-56 rounded-xl overflow-hidden shadow-xl z-50"
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid rgba(212,175,55,0.34)',
                        boxShadow: '0 18px 48px rgba(76,42,110,0.18), 0 4px 12px rgba(31,42,58,0.08)',
                        backdropFilter: 'blur(20px)'
                      }}
                    >
                      <div className="p-3 border-b border-white/10">
                        <p className="text-sm font-medium text-white">{user?.contact_name || 'Utilisateur'}</p>
                        <p className="text-xs text-white/50 truncate">{user?.email}</p>
                        {user?.company_name && (
                          <p className="text-xs text-[#D9B35A] mt-1">{user.company_name}</p>
                        )}
                      </div>
                      {/* Buyer/member section */}
                      <div className="p-2">
                        {nav.dropdown.buyer.map((item) => {
                          const Icon = item.icon;
                          return (
                            <Link
                              key={item.href}
                              to={item.href}
                              className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                              onClick={() => setShowUserMenu(false)}
                              data-testid={`user-menu-${item.href.replace(/\//g, '-')}`}
                            >
                              <Icon className="w-4 h-4" />
                              {item.label}
                              {item.href === '/wallet' && (
                                <span className="ml-auto text-xs text-[#D9B35A]">{user?.credits || 0} cr</span>
                              )}
                            </Link>
                          );
                        })}
                        <Link
                          to="/notifications"
                          className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                          onClick={() => setShowUserMenu(false)}
                          data-testid="user-menu-notifications"
                        >
                          <Bell className="w-4 h-4" />
                          Notifications
                          {unreadCount > 0 && (
                            <span className="ml-auto text-xs bg-red-500 text-white rounded-full px-1.5">{unreadCount}</span>
                          )}
                        </Link>
                      </div>

                      {/* Vendor section */}
                      {nav.dropdown.vendor.length > 0 && (
                        <div className="p-2 border-t border-white/10">
                          <p className="text-[10px] uppercase tracking-wider text-white/40 px-3 pt-1 pb-1.5 font-semibold">Vendeur</p>
                          {nav.dropdown.vendor.map((item) => {
                            const Icon = item.icon;
                            return (
                              <Link
                                key={item.href}
                                to={item.href}
                                className="flex items-center gap-2 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] rounded-lg"
                                onClick={() => setShowUserMenu(false)}
                              >
                                <Icon className="w-4 h-4" />
                                {item.label}
                              </Link>
                            );
                          })}
                        </div>
                      )}

                      {/* Admin section */}
                      {nav.dropdown.admin.length > 0 && (
                        <div className="p-2 border-t border-white/10">
                          <p className="text-[10px] uppercase tracking-wider text-[#D9B35A]/70 px-3 pt-1 pb-1.5 font-semibold flex items-center gap-1">
                            <Shield className="w-3 h-3" /> Administration
                          </p>
                          {nav.dropdown.admin.map((item) => {
                            const Icon = item.icon;
                            return (
                              <Link
                                key={item.href}
                                to={item.href}
                                className="flex items-center gap-2 px-3 py-2 text-sm text-[#D9B35A] hover:bg-[#D9B35A]/10 rounded-lg"
                                onClick={() => setShowUserMenu(false)}
                                data-testid={`admin-menu-${item.href.replace(/\//g, '-')}`}
                              >
                                <Icon className="w-4 h-4" />
                                {item.label}
                              </Link>
                            );
                          })}
                        </div>
                      )}

                      <div className="p-2 border-t border-white/10">
                        <button
                          onClick={() => {
                            setShowUserMenu(false);
                            handleLogout();
                          }}
                          className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg w-full"
                          data-testid="user-menu-logout"
                        >
                          <LogOut className="w-4 h-4" />
                          Déconnexion
                        </button>
                      </div>
                    </div>
                  )}
                </div>
);
