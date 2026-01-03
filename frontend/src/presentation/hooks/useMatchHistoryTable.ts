import { useState, useMemo, ChangeEvent } from "react";
import { MatchPredictionHistory, MatchHistoryTableProps } from "../../types";

export type SortColumn = "date" | "result" | "default";
export type SortDirection = "asc" | "desc";

interface UseMatchHistoryTableReturn {
  // State
  page: number;
  rowsPerPage: number;
  searchQuery: string;
  expandedRow: string | null;
  sortColumn: SortColumn;
  sortDirection: SortDirection;

  // Data
  paginatedMatches: MatchPredictionHistory[];
  totalMatches: number;
  isEmpty: boolean;

  // Handlers
  handleSort: (column: SortColumn) => void;
  handleChangePage: (event: unknown, newPage: number) => void;
  handleChangeRowsPerPage: (event: ChangeEvent<HTMLInputElement>) => void;
  handleSearchChange: (event: ChangeEvent<HTMLInputElement>) => void;
  handleToggleExpand: (matchId: string) => void;
}

export const useMatchHistoryTable = ({
  matches,
}: MatchHistoryTableProps): UseMatchHistoryTableReturn => {
  const [sortColumn, setSortColumn] = useState<SortColumn>("default");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState("");

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(column);
      setSortDirection("desc");
    }
  };

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
    setPage(0);
  };

  const handleToggleExpand = (matchId: string) => {
    setExpandedRow((prev) => (prev === matchId ? null : matchId));
  };

  const filteredMatches = useMemo(() => {
    if (!matches) return [];
    if (!searchQuery) return matches;
    const lowerQuery = searchQuery.toLowerCase();
    return matches.filter(
      (match) =>
        match.home_team.toLowerCase().includes(lowerQuery) ||
        match.away_team.toLowerCase().includes(lowerQuery)
    );
  }, [matches, searchQuery]);

  const sortedMatches = useMemo(() => {
    if (!filteredMatches || filteredMatches.length === 0) return [];
    const sorted = [...filteredMatches];

    const getTime = (m: MatchPredictionHistory) =>
      new Date(m.match_date).getTime();

    if (sortColumn === "date") {
      sorted.sort((a, b) => {
        const timeA = getTime(a);
        const timeB = getTime(b);
        return sortDirection === "asc" ? timeA - timeB : timeB - timeA;
      });
    } else if (sortColumn === "result") {
      sorted.sort((a, b) => {
        const getCorrectness = (m: MatchPredictionHistory) =>
          m.was_correct ? 1 : 0;
        const valA = getCorrectness(a);
        const valB = getCorrectness(b);

        if (valA !== valB) {
          return sortDirection === "asc" ? valA - valB : valB - valA;
        }
        return getTime(b) - getTime(a);
      });
    } else {
      sorted.sort((a, b) => getTime(b) - getTime(a));
    }

    return sorted;
  }, [filteredMatches, sortColumn, sortDirection]);

  const paginatedMatches = useMemo(
    () =>
      sortedMatches.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [sortedMatches, page, rowsPerPage]
  );

  return {
    page,
    rowsPerPage,
    searchQuery,
    expandedRow,
    sortColumn,
    sortDirection,
    paginatedMatches,
    totalMatches: sortedMatches.length,
    isEmpty: !matches || matches.length === 0,
    handleSort,
    handleChangePage,
    handleChangeRowsPerPage,
    handleSearchChange,
    handleToggleExpand,
  };
};
