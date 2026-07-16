import { Link } from 'react-router-dom';
import {
  Wallet, TrendingUp, Calendar, CreditCard, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { TabsContent } from '../ui/tabs';
import { formatCurrency, formatShortDate, TRANSACTION_TYPE } from './buyerUtils';

export const BuyerWalletTab = ({ wallet, transactions }) => (
          <TabsContent value="wallet" className="space-y-6">
            {/* Balance Card */}
            <Card className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border-purple-500/30">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white/60 mb-1">Solde disponible</p>
                    <p className="text-4xl font-bold text-white" data-testid="wallet-balance">
                      {formatCurrency(wallet?.balance_cents || wallet?.balance_credits * 100 || 0)}
                    </p>
                    <p className="text-sm text-white/50 mt-2">
                      Crédits O'SCOP pour vos commandes
                    </p>
                  </div>
                  <div className="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center">
                    <Wallet className="w-8 h-8 text-purple-400" />
                  </div>
                </div>
                <div className="mt-6 flex gap-3">
                  <Link to="/wallet" className="flex-1">
                    <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white" data-testid="topup-wallet-btn">
                      <CreditCard className="w-4 h-4 mr-2" />
                      Recharger
                    </Button>
                  </Link>
                  <Button variant="outline" className="border-white/20 text-white/80" data-testid="wallet-history-btn">
                    <Calendar className="w-4 h-4 mr-2" />
                    Historique
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Recent Transactions */}
            <Card className="bg-white/[0.04] border-white/[0.08]">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                  Transactions récentes
                </CardTitle>
              </CardHeader>
              <CardContent>
                {transactions.length === 0 ? (
                  <div className="text-center py-8 text-white/50" data-testid="no-transactions">
                    <Wallet className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Aucune transaction</p>
                    <p className="text-sm mt-2">Vos transactions apparaîtront ici</p>
                  </div>
                ) : (
                  <div className="space-y-3" data-testid="transactions-list">
                    {transactions.slice(0, 10).map((tx, idx) => {
                      // Determine transaction type based on direction or type
                      const isCredit = tx.direction === 'CREDIT' || tx.type === 'CREDIT_PURCHASE' || tx.type === 'REFUND';
                      const txLabel = tx.reason_code || tx.type || 'Transaction';
                      const txDescription = tx.description || tx.correlation_id || formatShortDate(tx.created_at);
                      const txAmount = tx.amount_credits * 100 || tx.amount_cents || tx.amount || 0;
                      
                      return (
                        <div 
                          key={tx.id || idx}
                          className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between"
                          data-testid={`transaction-${tx.id || idx}`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                              isCredit ? 'bg-emerald-500/20' : 'bg-orange-500/20'
                            }`}>
                              {isCredit ? (
                                <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                              ) : (
                                <ArrowDownRight className="w-4 h-4 text-orange-400" />
                              )}
                            </div>
                            <div>
                              <p className="font-medium text-white/90 text-sm">
                                {txLabel.replace(/_/g, ' ')}
                              </p>
                              <p className="text-xs text-white/50">{txDescription}</p>
                            </div>
                          </div>
                          <p className={`font-semibold ${isCredit ? 'text-emerald-400' : 'text-orange-400'}`}>
                            {isCredit ? '+' : '-'}{formatCurrency(Math.abs(txAmount))}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
);
