import React, { useState, useEffect } from "react";
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
    nickname: "",
    battle_tag: "",
    race: ""
  });
  const [loading, setLoading] = useState(false);
  const [matchStatus, setMatchStatus] = useState(null);
  const [error, setError] = useState("");
  const [lastChecked, setLastChecked] = useState(null);
  const [autoMonitoring, setAutoMonitoring] = useState(false);
  const [intervalId, setIntervalId] = useState(null);

  const races = [
    { value: "Human", label: "Human", icon: "⚔️" },
    { value: "Orc", label: "Orc", icon: "🪓" },
    { value: "Night Elf", label: "Night Elf", icon: "🏹" },
    { value: "Undead", label: "Undead", icon: "💀" },
    { value: "Random", label: "Random", icon: "🎲" }
  ];

  const handleInputChange = (field, value) => {
    setPlayerData(prev => ({ ...prev, [field]: value }));
    setError("");
  };

  const validateBattleTag = (battleTag) => {
    const regex = /^[a-zA-Z0-9]+#\d{4,5}$/;
    return regex.test(battleTag);
  };

  const checkMatch = async (silent = false) => {
    if (!playerData.nickname || !playerData.battle_tag || !playerData.race) {
      setError("Please fill in all fields");
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
    if (!playerData.nickname || !playerData.battle_tag || !playerData.race) {
      setError("Please fill in all fields before starting auto-monitoring");
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

  const showDemoMatch = () => {
    // Set form data for demo
    const demoPlayerData = {
      nickname: "DemoPlayer",
      battle_tag: "DemoPlayer#1234", 
      race: "Human"
    };
    
    setPlayerData(demoPlayerData);
    
    // Demo data to show what happens when a match is found
    const demoMatchData = {
      status: "in_game",
      message: "Player TestPlayer#1234 is currently in game",
      data: {
        id: "demo-match-id",
        battle_tag: currentPlayerData.battle_tag,
        is_in_game: true,
        match_data: {
          id: "demo-match",
          map: "Lost Temple",
          matchType: "1v1"
        },
        opponent_data: {
          opponents: [
            {
              battle_tag: "ProGamer#5678",
              race: "Orc",
              statistics: {
                raceStats: [
                  {
                    race: "vs Human",
                    wins: 127,
                    losses: 89,
                    games: 216,
                    winrate: 0.588
                  }
                ]
              },
              recent_matches: {
                matches: [
                  {
                    map: "Lost Temple",
                    won: true,
                    durationInSeconds: 852,
                    heroUsed: "Blademaster"
                  },
                  {
                    map: "Lost Temple", 
                    won: false,
                    durationInSeconds: 1234,
                    heroUsed: "Far Seer"
                  },
                  {
                    map: "Twisted Meadows",
                    won: true,
                    durationInSeconds: 456,
                    heroUsed: "Blademaster"
                  }
                ]
              },
              hero_stats: {
                heroStatsItemList: [
                  {
                    heroId: "blademaster",
                    stats: [
                      {
                        race: 1,
                        winLossesOnMap: [
                          {
                            map: "Overall",
                            winLosses: [
                              {
                                race: 1, // vs Human
                                wins: 23,
                                losses: 12,
                                games: 35,
                                winrate: 0.657
                              }
                            ]
                          },
                          {
                            map: "2506221057LastRefugev1_5",
                            winLosses: [
                              {
                                race: 1,
                                wins: 8,
                                losses: 2,
                                games: 10,
                                winrate: 0.8
                              }
                            ]
                          }
                        ]
                      }
                    ]
                  },
                  {
                    heroId: "farseer",
                    stats: [
                      {
                        race: 1,
                        winLossesOnMap: [
                          {
                            map: "Overall",
                            winLosses: [
                              {
                                race: 1,
                                wins: 15,
                                losses: 18,
                                games: 33,
                                winrate: 0.455
                              }
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ]
        },
        timestamp: new Date().toISOString()
      }
    };
    
    setMatchStatus(demoMatchData);
    setLastChecked(new Date());
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
    const race = races.find(r => r.value === raceName);
    return race?.icon || "❓";
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
      "tinker": "⚙️"
    };
    return heroIcons[heroId] || "⭐";
  };

  const getPlayerRaceNumber = () => {
    const raceMap = {
      "Human": 1,
      "Orc": 2,
      "Night Elf": 4,
      "Undead": 8,
      "Random": 16
    };
    return raceMap[playerData.race] || 1;
  };

  const OpponentCard = ({ opponent }) => {
    const playerRaceNum = getPlayerRaceNumber();
    
    return (
      <Card className="bg-slate-800/50 border-amber-600/30" data-testid={`opponent-card-${opponent.battle_tag}`}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-amber-400">
            <User className="w-5 h-5" />
            {opponent.battle_tag}
            <Badge variant="secondary" className="bg-amber-600/20 text-amber-300">
              {getRaceIcon(opponent.race)} {opponent.race}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Hero Statistics vs Your Race */}
          {opponent.hero_stats?.heroStatsItemList && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-purple-400">
                <Shield className="w-4 h-4" />
                <span className="text-sm font-semibold">Hero Picks vs {playerData.race}</span>
              </div>
              <div className="grid gap-2 max-h-64 overflow-y-auto">
                {opponent.hero_stats.heroStatsItemList.map((heroStat, idx) => {
                  // Find stats for this hero against your race
                  const heroVsYourRace = heroStat.stats.find(stat => 
                    stat.winLossesOnMap.some(mapStat => 
                      mapStat.winLosses.some(winLoss => winLoss.race === playerRaceNum && winLoss.games > 0)
                    )
                  );
                  
                  if (!heroVsYourRace) return null;
                  
                  const overallStats = heroVsYourRace.winLossesOnMap.find(map => map.map === "Overall");
                  const vsYourRaceStats = overallStats?.winLosses.find(wl => wl.race === playerRaceNum);
                  
                  if (!vsYourRaceStats || vsYourRaceStats.games === 0) return null;
                  
                  return (
                    <div key={idx} className="bg-slate-700/50 p-3 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{getHeroIcon(heroStat.heroId)}</span>
                          <span className="text-amber-300 font-medium capitalize">
                            {heroStat.heroId.replace(/([A-Z])/g, ' $1').trim()}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className={`font-semibold ${vsYourRaceStats.winrate > 0.6 ? 'text-red-400' : 
                            vsYourRaceStats.winrate > 0.4 ? 'text-yellow-400' : 'text-green-400'}`}>
                            {Math.round(vsYourRaceStats.winrate * 100)}%
                          </div>
                          <div className="text-xs text-slate-400">
                            {vsYourRaceStats.wins}W-{vsYourRaceStats.losses}L
                          </div>
                        </div>
                      </div>
                      
                      {/* Map specific stats */}
                      <div className="space-y-1">
                        {heroVsYourRace.winLossesOnMap.filter(mapStat => 
                          mapStat.map !== "Overall" && 
                          mapStat.winLosses.some(wl => wl.race === playerRaceNum && wl.games > 0)
                        ).slice(0, 3).map((mapStat, mapIdx) => {
                          const mapVsYou = mapStat.winLosses.find(wl => wl.race === playerRaceNum);
                          if (!mapVsYou || mapVsYou.games === 0) return null;
                          
                          return (
                            <div key={mapIdx} className="text-xs flex justify-between text-slate-300">
                              <span className="truncate max-w-32">{mapStat.map.replace(/^\d+/, '').replace(/v\d+_\d+$/, '')}</span>
                              <span className={mapVsYou.winrate > 0.6 ? 'text-red-300' : 
                                mapVsYou.winrate > 0.4 ? 'text-yellow-300' : 'text-green-300'}>
                                {Math.round(mapVsYou.winrate * 100)}% ({mapVsYou.games})
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Overall Statistics */}
          {opponent.statistics && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-green-400">
                  <Trophy className="w-4 h-4" />
                  <span className="text-sm">Overall Stats</span>
                </div>
                {opponent.statistics.raceStats?.map((stat, idx) => (
                  <div key={idx} className="text-sm bg-slate-700/50 p-2 rounded">
                    <div className="flex justify-between">
                      <span>{getRaceIcon(stat.race)} vs {playerData.race}</span>
                      <span className="text-amber-300">{formatWinRate(stat.wins, stat.losses)}</span>
                    </div>
                    <div className="text-xs text-slate-400">
                      {stat.wins}W - {stat.losses}L ({stat.games} games)
                    </div>
                  </div>
                )) || <div className="text-sm text-slate-400">No race statistics available</div>}
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-blue-400">
                  <Target className="w-4 h-4" />
                  <span className="text-sm">Recent Matches</span>
                </div>
                {opponent.recent_matches?.matches?.slice(0, 5).map((match, idx) => (
                  <div key={idx} className="text-xs bg-slate-700/50 p-2 rounded">
                    <div className="flex justify-between items-center">
                      <span className="text-amber-300 truncate">{match.map?.replace(/^\d+/, '') || "Unknown"}</span>
                      <Badge 
                        variant={match.won ? "success" : "destructive"}
                        className={match.won ? "bg-green-600/20 text-green-300" : "bg-red-600/20 text-red-300"}
                      >
                        {match.won ? "W" : "L"}
                      </Badge>
                    </div>
                    <div className="text-slate-400 mt-1">
                      {Math.round(match.durationInSeconds / 60)}m
                      {match.heroUsed && <span className="ml-2">{getHeroIcon(match.heroUsed.toLowerCase())}</span>}
                    </div>
                  </div>
                )) || <div className="text-sm text-slate-400">No recent matches found</div>}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
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
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="nickname" className="text-slate-200">Nickname</Label>
                <Input
                  id="nickname"
                  data-testid="nickname-input"
                  placeholder="Enter your nickname"
                  value={playerData.nickname}
                  onChange={(e) => handleInputChange("nickname", e.target.value)}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="battle-tag" className="text-slate-200">Battle Tag</Label>
                <Input
                  id="battle-tag"
                  data-testid="battle-tag-input"
                  placeholder="PlayerName#1234"
                  value={playerData.battle_tag}
                  onChange={(e) => handleInputChange("battle_tag", e.target.value)}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-slate-200">Race</Label>
              <select
                data-testid="race-selector"
                value={playerData.race}
                onChange={(e) => handleInputChange("race", e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 text-white rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-600"
              >
                <option value="">Select your race</option>
                {races.map(race => (
                  <option key={race.value} value={race.value}>
                    {race.icon} {race.label}
                  </option>
                ))}
              </select>
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
                  <h2 className="text-2xl font-bold text-amber-400 mb-2">Opponent Analysis</h2>
                  <Separator className="bg-amber-600/30" />
                </div>
                <div className="grid gap-6">
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