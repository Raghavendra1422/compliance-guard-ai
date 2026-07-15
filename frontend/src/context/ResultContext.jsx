import { createContext, useContext, useState } from 'react'

const ResultContext = createContext(null)

export function ResultProvider({ children }) {
  const [result, setResult] = useState(null)

  return (
    <ResultContext.Provider value={{ result, setResult }}>
      {children}
    </ResultContext.Provider>
  )
}

export function useResult() {
  return useContext(ResultContext)
}