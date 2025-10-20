import React, { useState, useEffect, useRef } from "react";
import "@/App.css";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
// Select component replaced with native HTML select
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Sword, Trophy, Target, User, Clock, Shield } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [playerData, setPlayerData] = useState({
    battle_tag: ""
  });
  
  // Add ref for direct DOM manipulation as fallback
  const battleTagRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [matchStatus, setMatchStatus] = useState(null);
  const [error, setError] = useState("");
  const [lastChecked, setLastChecked] = useState(null);
  const [autoMonitoring, setAutoMonitoring] = useState(false);
  const [intervalId, setIntervalId] = useState(null);

  // Races array removed - race icons now handled inline

  const handleInputChange = (field, value) => {
    console.log('Form change:', field, value);
    setPlayerData(prev => {
      const newData = { ...prev, [field]: value };
      console.log('New player data:', newData);
      return newData;
    });
    setError("");
  };

  const validateBattleTag = (battleTag) => {
    // Support international characters including Cyrillic
    const regex = /^[\w\u0400-\u04FF\u0500-\u052F]+#\d{4,5}$/u;
    return regex.test(battleTag);
  };

  const checkMatch = async (silent = false) => {
    if (!playerData.battle_tag) {
      setError("Please enter a battle tag");
      return;
    }

    if (!validateBattleTag(playerData.battle_tag)) {
      setError("Battle tag must be in format PlayerName#1234");
      return;
    }

    if (!silent) setLoading(true);
    setError("");
    
    try {
      const response = await axios.post(`${API}/check-match`, playerData);
      setMatchStatus(response.data);
      setLastChecked(new Date());
    } catch (err) {
      console.error("Error checking match:", err);
      setError(err.response?.data?.detail || "Failed to check match status");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const startAutoMonitoring = () => {
    if (!playerData.battle_tag) {
      setError("Please enter a battle tag before starting auto-monitoring");
      return;
    }

    if (!validateBattleTag(playerData.battle_tag)) {
      setError("Battle tag must be in format PlayerName#1234");
      return;
    }

    setAutoMonitoring(true);
    
    // First check immediately
    checkMatch(true);
    
    // Then check every 5 seconds
    const id = setInterval(() => {
      checkMatch(true);
    }, 5000);
    
    setIntervalId(id);
  };

  const stopAutoMonitoring = () => {
    setAutoMonitoring(false);
    if (intervalId) {
      clearInterval(intervalId);
      setIntervalId(null);
    }
  };

  const showDemoMatch = async () => {
    console.log('Demo button clicked - fetching real data');
    setLoading(true);
    setError(""); // Clear any existing errors
    
    try {
      // Set battle tag for demo
      const demoPlayerData = {
        battle_tag: "DemoPlayer#1234"
      };
      
      // Force state update and wait for it
      await new Promise((resolve) => {
        setPlayerData(demoPlayerData);
        setTimeout(resolve, 100); // Give React time to update
      });
      
      // FORCE DOM update as backup
      setTimeout(() => {
        if (battleTagRef.current) {
          battleTagRef.current.value = demoPlayerData.battle_tag;  
          battleTagRef.current.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }, 150);
      
      // Fetch real demo match data from backend
      console.log('Fetching demo match data...');
      const response = await axios.get(`${API}/demo-match`);
      console.log('Demo match data received:', response.data);
      
      setMatchStatus(response.data);
      setLastChecked(new Date());
      
      console.log('Demo match setup complete');
      
    } catch (err) {
      console.error("Error fetching demo match:", err);
      setError(`Failed to load demo match data: ${err.message}`);
    } finally {
      setLoading(false);
    }
    
    // Static demo data removed - now using real backend data
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [intervalId]);

  const getRaceIcon = (raceName) => {
    const raceIcons = {
      "Human": "⚔️",
      "Orc": "🪓", 
      "Night Elf": "🏹",
      "Undead": "💀",
      "Random": "🎲"
    };
    return raceIcons[raceName] || "❓";
  };

  const formatWinRate = (wins, losses) => {
    const total = wins + losses;
    if (total === 0) return "0%";
    return `${Math.round((wins / total) * 100)}%`;
  };

  const getHeroIcon = (heroId) => {
    const heroIcons = {
      "archmage": "🔮",
      "mountainking": "⚒️",
      "paladin": "🛡️",
      "bloodmage": "🩸",
      "blademaster": "⚔️",
      "farseer": "🌩️",
      "taurenchieftain": "🐂",
      "shadowhunter": "🏹",
      "demonhunter": "😈",
      "keeperofthegrove": "🌳",
      "moonpriestess": "🌙",
      "warden": "🦉",
      "deathknight": "💀",
      "dreadlord": "👹",
      "lich": "❄️",
      "cryptlord": "🕷️",
      "tinker": "⚙️",
      "bansheeranger": "⭐",
      "avatarofflame": "🔥"
    };
    return heroIcons[heroId] || "⭐";
  };

  // Map heroes to their races
  const getHeroesByRace = (race) => {
    const herosByRace = {
      "Human": ["archmage", "mountainking", "paladin", "bloodmage"],
      "Orc": ["blademaster", "farseer", "taurenchieftain", "shadowhunter"],
      "Night Elf": ["demonhunter", "keeperofthegrove", "moonpriestess", "warden", "bansheeranger"],
      "Undead": ["deathknight", "dreadlord", "lich", "cryptlord"],
      "Random": [] // Random can use any heroes
    };
    return herosByRace[race] || [];
  };

  const get_race_name_from_number = (raceNum) => {
    const raceMap = {
      0: "Random",
      1: "Human",
      2: "Orc",
      4: "Night Elf",
      8: "Undead",
      16: "Random"
    };
    return raceMap[raceNum] || "Unknown";
  };

  const OpponentCard = ({ opponent }) => {
    // Find most played hero
    const getMostPlayedHero = () => {
      if (!opponent.hero_stats?.heroStatsItemList) return null;
      
      let maxGames = 0;
      let mostPlayedHero = null;
      
      opponent.hero_stats.heroStatsItemList.forEach(heroStat => {
        let totalGames = 0;
        heroStat.stats?.forEach(stat => {
          const overall = stat.winLossesOnMap?.find(wl => wl.map === "Overall");
          if (overall) {
            overall.winLosses?.forEach(wl => {
              totalGames += wl.games || 0;
            });
          }
        });
        
        if (totalGames > maxGames) {
          maxGames = totalGames;
          mostPlayedHero = {
            heroId: heroStat.heroId,
            games: totalGames
          };
        }
      });
      
      return mostPlayedHero;
    };

    // Calculate overall winrate
    const getOverallWinrate = () => {
      if (!opponent.basic_stats?.winLosses) return null;
      
      let totalWins = 0;
      let totalGames = 0;
      
      opponent.basic_stats.winLosses.forEach(wl => {
        totalWins += wl.wins || 0;
        totalGames += wl.games || 0;
      });
      
      return totalGames > 0 ? Math.round((totalWins / totalGames) * 100) : 0;
    };

    const mostPlayedHero = getMostPlayedHero();
    const overallWinrate = getOverallWinrate();
    
    return (
      <div className="bg-slate-800/50 border border-amber-600/30 rounded-lg p-4 mb-4">
        <div className="grid grid-cols-3 gap-4 items-center">
          {/* Column 1: Hero */}
          <div className="flex items-center gap-3">
            <div className="text-amber-400 font-semibold">
              {getRaceIcon(opponent.race)} {opponent.battle_tag}
            </div>
            {mostPlayedHero && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-lg">{getHeroIcon(mostPlayedHero.heroId)}</span>
                <span className="text-slate-300 capitalize">
                  {mostPlayedHero.heroId}
                </span>
                <span className="text-xs text-slate-500">
                  ({mostPlayedHero.games} игр)
                </span>
              </div>
            )}
          </div>
          
          {/* Column 2: Winrate */}
          <div className="text-center">
            {overallWinrate !== null && (
              <div className={`text-2xl font-bold ${
                overallWinrate >= 65 ? 'text-red-400' : 
                overallWinrate >= 50 ? 'text-yellow-400' : 'text-green-400'
              }`}>
                {overallWinrate}%
              </div>
            )}
            <div className="text-xs text-slate-400">винрейт</div>
          </div>
          
          {/* Column 3: Achievements */}
          <div className="flex flex-col gap-1 justify-end">
            {opponent.achievements?.slice(0, 3).map((achievement, idx) => (
              <div key={idx} className="flex flex-col items-end">
                <Badge 
                  className={`text-xs ${
                    achievement.color === 'blue' ? 'bg-blue-600/20 text-blue-300' :
                    achievement.color === 'red' ? 'bg-red-600/20 text-red-300' :
                    achievement.color === 'purple' ? 'bg-purple-600/20 text-purple-300' :
                    achievement.color === 'green' ? 'bg-green-600/20 text-green-300' :
                    achievement.color === 'yellow' ? 'bg-yellow-600/20 text-yellow-300' :
                    'bg-slate-600/20 text-slate-300'
                  }`}
                >
                  {achievement.title.split(' ')[0]} {/* Show emoji */}
                </Badge>
                <span className="text-xs text-slate-400 text-right mt-1">
                  {achievement.title.split(' ').slice(1).join(' ')} {/* Show title without emoji */}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-500 mb-4">
            W3Champions Match Scout
          </h1>
          <p className="text-slate-300 text-lg max-w-2xl mx-auto">
            Monitor your Warcraft III matches and scout your opponents in real-time
          </p>
        </div>

        {/* Player Input Form */}
        <Card className="max-w-2xl mx-auto mb-8 bg-slate-800/50 border-amber-600/30" data-testid="player-input-form">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-400">
              <Shield className="w-5 h-5" />
              Player Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="battle-tag" className="text-slate-200">Battle Tag</Label>
              <Input
                id="battle-tag"
                ref={battleTagRef}
                data-testid="battle-tag-input"
                placeholder="PlayerName#1234"
                value={playerData.battle_tag}
                onChange={(e) => handleInputChange("battle_tag", e.target.value)}
                className="bg-slate-700 border-slate-600 text-white placeholder-slate-400"
              />
            </div>

            {error && (
              <Alert className="border-red-600/50 bg-red-600/10">
                <AlertDescription className="text-red-400">{error}</AlertDescription>
              </Alert>
            )}

            <div className="grid md:grid-cols-2 gap-3">
              <Button
                onClick={() => checkMatch()}
                disabled={loading || autoMonitoring}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                data-testid="check-match-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Checking...
                  </>
                ) : (
                  <>
                    <Sword className="w-4 h-4 mr-2" />
                    Check Now
                  </>
                )}
              </Button>
              
              {!autoMonitoring ? (
                <Button
                  onClick={startAutoMonitoring}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  data-testid="start-monitoring-btn"
                >
                  <Target className="w-4 h-4 mr-2" />
                  Auto Monitor (5s)
                </Button>
              ) : (
                <Button
                  onClick={stopAutoMonitoring}
                  className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  data-testid="stop-monitoring-btn"
                >
                  <Clock className="w-4 h-4 mr-2" />
                  Stop Monitoring
                </Button>
              )}
            </div>

            {(lastChecked || autoMonitoring) && (
              <div className="flex items-center gap-4 text-sm justify-center">
                {lastChecked && (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Clock className="w-4 h-4" />
                    Last checked: {lastChecked.toLocaleTimeString()}
                  </div>
                )}
                {autoMonitoring && (
                  <div className="flex items-center gap-2 text-green-400">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    Auto monitoring active
                  </div>
                )}
              </div>
            )}
            
            {/* Demo button */}
            <div className="text-center mt-4">
              <Button
                onClick={showDemoMatch}
                variant="outline"
                className="border-amber-600/50 text-amber-400 hover:bg-amber-600/10"
                data-testid="demo-match-btn"
              >
                <Trophy className="w-4 h-4 mr-2" />
                Show Demo Match Found
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Removed static test data */}

        {/* Match Status Results */}
        {matchStatus && (
          <div className="max-w-6xl mx-auto" data-testid="match-results">
            <Card className="mb-6 bg-slate-800/50 border-amber-600/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-amber-400">
                  <Target className="w-5 h-5" />
                  Match Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                {matchStatus.status === "not_in_game" ? (
                  <Alert className="border-blue-600/50 bg-blue-600/10">
                    <AlertDescription className="text-blue-300">
                      Player {matchStatus.data.battle_tag} is not currently in a match.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert className="border-green-600/50 bg-green-600/10">
                    <AlertDescription className="text-green-300">
                      Match found! Player {matchStatus.data.battle_tag} is currently in game.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Opponent Information */}
            {matchStatus && matchStatus.status === "in_game" && matchStatus.data && matchStatus.data.opponent_data && matchStatus.data.opponent_data.opponents && matchStatus.data.opponent_data.opponents.length > 0 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-amber-400 mb-4">🎯 Анализ Противника</h2>
                  
                  {/* Table Headers */}
                  <div className="bg-slate-700/30 border border-slate-600/30 rounded-lg p-3 mb-4">
                    <div className="grid grid-cols-3 gap-4 text-sm font-medium text-slate-300">
                      <div className="text-left">👤 Игрок & Герой</div>
                      <div className="text-center">📊 Винрейт</div>
                      <div className="text-right">🏆 Достижения</div>
                    </div>
                  </div>
                  
                  <Separator className="bg-amber-600/30 mb-4" />
                </div>
                <div className="space-y-2">
                  {matchStatus.data.opponent_data.opponents.map((opponent, index) => (
                    <OpponentCard key={index} opponent={opponent} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;