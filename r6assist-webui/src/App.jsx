import { useEffect, useState } from 'react'
import { io } from 'socket.io-client'
import { AlertCircle, Target, Shield, Users, Crosshair, HelpCircle, Globe } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import enUs from './locales/en-us.json'
import zhTw from './locales/zh-tw.json'

// Define the Socket URL. In dev it will be the flask server.
const SOCKET_URL = 'http://localhost:5000'
const translations = {
  'en-us': enUs,
  'zh-tw': zhTw
}

function App() {
  const [lang, setLang] = useState('en-us')
  const [socket, setSocket] = useState(null)
  const [gameState, setGameState] = useState({
    status: 'idle', // idle, waiting, active
    message: translations[lang].connecting,
    side: null,
    user_pick: null,
    user_score: 0,
    teammates: [],
    missing_roles: [],
    recommendations: []
  })

  useEffect(() => {
    // Connect to the WebSocket server
    const newSocket = io(SOCKET_URL)
    setSocket(newSocket)

    newSocket.on('connect', () => {
      console.log('Connected to backend')
      newSocket.emit('start_monitoring') // Automatically start on connect
    })

    newSocket.on('gameState', (data) => {
      console.log('Received Game State:', data)
      setGameState(data)
    })

    newSocket.on('disconnect', () => {
      console.log('Disconnected from backend')
      setGameState(prev => ({ ...prev, status: 'idle', message: 'connection_lost' }))
    })

    return () => newSocket.close()
  }, [])

  const t = translations[lang]

  // Render helpers
  const getSideColor = (side) => side === 'atk' ? 'text-amber-500' : side === 'def' ? 'text-indigo-400' : 'text-slate-400'
  const getSideIcon = (side) => side === 'atk' ? <Target className="w-6 h-6" /> : side === 'def' ? <Shield className="w-6 h-6" /> : <HelpCircle className="w-6 h-6" />
  const getSideLabel = (side) => side === 'atk' ? t.attack : side === 'def' ? t.defense : t.unknown

  const getScoreColor = (score) => {
    if (score >= 8) return 'bg-emerald-500 text-emerald-100 shadow-[0_0_15px_rgba(16,185,129,0.5)]'
    if (score >= 5) return 'bg-amber-500 text-amber-100 shadow-[0_0_15px_rgba(245,158,11,0.5)]'
    return 'bg-rose-500 text-rose-100 shadow-[0_0_15px_rgba(244,63,94,0.5)]'
  }

  // Determine display message (dynamic from local state or server)
  const displayMessage = gameState.message === 'connection_lost' ? t.connection_lost :
    gameState.message === 'Connecting to R6Assist Core...' ? t.connecting :
      gameState.message

  // Waiting State
  if (gameState.status !== 'active') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 subtle-bg bg-fixed bg-cover bg-center text-slate-100">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/20 via-slate-900/40 to-slate-900 -z-10" />

        {/* Language Switcher */}
        <div className="absolute top-6 right-6 flex items-center gap-2">
          <Globe className="w-5 h-5 text-slate-400" />
          <select
            className="bg-slate-800/80 border border-slate-700 text-slate-200 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2 outline-none cursor-pointer"
            value={lang}
            onChange={(e) => setLang(e.target.value)}
          >
            <option value="en-us">English</option>
            <option value="zh-tw">繁體中文</option>
          </select>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel p-8 rounded-3xl max-w-md w-full text-center flex flex-col items-center gap-6"
        >
          <div className="relative">
            <div className="w-20 h-20 rounded-full border-4 border-indigo-500/30 border-t-indigo-500 animate-spin" />
            <Crosshair className="w-8 h-8 text-indigo-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-70" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-2">{t.terminal}</h1>
            <p className="text-slate-400">{displayMessage}</p>
          </div>
        </motion.div>
      </div>
    )
  }

  // Active Dashboard State
  return (
    <div className="min-h-screen p-4 md:p-8 flex flex-col relative overflow-hidden text-slate-100">
      <div className="absolute inset-0 bg-slate-950 -z-20" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,_var(--tw-gradient-stops))] from-indigo-900/20 via-transparent to-transparent -z-10 pointer-events-none" />

      {/* Language Switcher */}
      <div className="absolute top-4 right-4 md:top-8 md:right-8 flex items-center gap-2 z-50">
        <Globe className="w-5 h-5 text-slate-400" />
        <select
          className="bg-slate-800/80 border border-slate-700 text-slate-200 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-2 outline-none cursor-pointer shadow-lg backdrop-blur-sm"
          value={lang}
          onChange={(e) => setLang(e.target.value)}
        >
          <option value="en-us">EN</option>
          <option value="zh-tw">繁中</option>
        </select>
      </div>

      {/* Header Bar */}
      <header className="flex flex-col flex-wrap md:flex-row items-start md:items-center justify-between gap-4 mb-8 mt-12 md:mt-0 pr-0 md:pr-24">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-2xl glass-panel flex items-center justify-center ${getSideColor(gameState.side)}`}>
            {getSideIcon(gameState.side)}
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight uppercase flex items-center gap-3">
              {getSideLabel(gameState.side)} {t.phase}
            </h1>
            <div className="flex items-center gap-2 mt-1 text-slate-400 font-medium">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              {t.live_monitoring}
            </div>
          </div>
        </div>

        {/* Missing Roles Warning */}
        <AnimatePresence>
          {gameState.missing_roles && gameState.missing_roles.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center flex-wrap gap-3 px-5 py-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="font-semibold">{t.team_lacks}</span>
              <div className="flex flex-wrap gap-2">
                {gameState.missing_roles.map((role, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded-md bg-amber-500/20 text-sm whitespace-nowrap">{role}</span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1">

        {/* Left Column: Team Composition */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="glass-panel p-6 rounded-3xl flex-1 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
              <Users className="w-6 h-6 text-slate-400" />
              <h2 className="text-xl font-semibold">{t.active_roster}</h2>
            </div>

            <div className="space-y-4">
              <div className="flex flex-col gap-2">
                <span className="text-xs uppercase tracking-wider text-slate-500 font-bold">{t.your_selection}</span>
                <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-800/50 border border-slate-700/50">
                  <span className="text-xl font-bold">{gameState.user_pick || t.waiting}</span>
                  {gameState.user_pick !== 'Unknown' && (
                    <div className={`px-4 py-1.5 rounded-full font-bold text-sm ${getScoreColor(gameState.user_score)}`}>
                      {t.score} {gameState.user_score.toFixed(1)}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-2 mt-6">
                <span className="text-xs uppercase tracking-wider text-slate-500 font-bold">{t.teammates}</span>
                <div className="flex flex-col gap-2">
                  {gameState.teammates.map((mate, idx) => (
                    <div key={idx} className="flex items-center gap-4 p-3 rounded-xl bg-slate-800/30 border border-slate-700/30 text-slate-300">
                      <div className="w-8 h-8 rounded-lg bg-slate-700/50 flex items-center justify-center text-xs font-bold text-slate-400">P{idx + 1}</div>
                      <span className="font-medium">{mate}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Recommendations */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div>
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <Crosshair className="w-6 h-6 text-indigo-400" />
              {t.tactical_recommendations}
            </h2>

            <div className="grid gap-4">
              <AnimatePresence mode="popLayout">
                {gameState.recommendations.map((rec, index) => (
                  <motion.div
                    key={rec.name}
                    layout
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                    className={`relative overflow-hidden group rounded-3xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-6 transition-all duration-300
                            ${index === 0
                        ? 'bg-gradient-to-r from-indigo-600/20 to-violet-600/20 border border-indigo-500/30 shadow-[0_0_30px_rgba(99,102,241,0.1)]'
                        : 'glass-panel hover:bg-slate-800/60'
                      }`}
                  >
                    {/* Rank indicator for top choice */}
                    {index === 0 && (
                      <div className="absolute top-0 right-0 px-4 py-1 bg-indigo-500 text-indigo-50 text-xs font-bold rounded-bl-xl tracking-wider">
                        {t.optimal_choice}
                      </div>
                    )}

                    <div className="flex items-center gap-6 z-10">
                      <div className={`text-4xl font-black opacity-20 w-8 ${index === 0 ? 'text-indigo-400' : 'text-slate-500'}`}>
                        #{index + 1}
                      </div>
                      <div>
                        <h3 className={`text-2xl font-bold tracking-tight ${index === 0 ? 'text-indigo-100' : 'text-slate-200'}`}>
                          {rec.name}
                        </h3>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {rec.roles.map(r => (
                            <span key={r} className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
                              {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2 z-10">
                      <div className="flex items-baseline gap-1">
                        <span className={`text-3xl font-bold ${index === 0 ? 'text-indigo-400' : 'text-slate-100'}`}>
                          {rec.score.toFixed(1)}
                        </span>
                        <span className="text-slate-500 text-sm font-medium">/ 10</span>
                      </div>

                      {/* Score Bar */}
                      <div className="w-32 h-2 rounded-full bg-slate-800 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${(rec.score / 10) * 100}%` }}
                          transition={{ duration: 1, ease: 'easeOut' }}
                          className={`h-full rounded-full ${index === 0 ? 'bg-indigo-500' : 'bg-slate-400'}`}
                        />
                      </div>
                    </div>

                    {/* Subtle background glow for cards */}
                    <div className="absolute -right-20 -top-20 w-64 h-64 bg-white/5 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  </motion.div>
                ))}
              </AnimatePresence>

              {gameState.recommendations.length === 0 && (
                <div className="glass-panel p-8 rounded-3xl text-center text-slate-400">
                  {t.no_recommendations}
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}

export default App
