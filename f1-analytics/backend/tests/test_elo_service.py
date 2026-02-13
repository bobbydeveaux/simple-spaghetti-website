"""
Unit tests for ELO service.

Tests the ELO service layer that integrates with the database.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date

from app.models.f1_models import Driver, Team, Race, RaceResult, RaceStatus, ResultStatus
from app.services.elo_service import ELOService, get_elo_service


class TestELOService:
    """Test suite for ELO service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.service = ELOService(self.mock_db, k_factor=32)

    def test_initialization(self):
        """Test service initialization."""
        assert self.service.db == self.mock_db
        assert self.service.calculator.k_factor == 32

        # Test custom k_factor
        custom_service = ELOService(self.mock_db, k_factor=24)
        assert custom_service.calculator.k_factor == 24

    def test_get_current_driver_ratings(self):
        """Test getting current driver ratings."""
        # Mock drivers
        mock_drivers = [
            Mock(driver_id=1, current_elo_rating=1600),
            Mock(driver_id=2, current_elo_rating=1500),
            Mock(driver_id=3, current_elo_rating=1400)
        ]
        self.mock_db.query.return_value.all.return_value = mock_drivers

        ratings = self.service.get_current_driver_ratings()

        assert ratings == {1: 1600, 2: 1500, 3: 1400}
        self.mock_db.query.assert_called_with(Driver)

    def test_get_current_team_ratings(self):
        """Test getting current team ratings."""
        # Mock teams
        mock_teams = [
            Mock(team_id=100, current_elo_rating=1650),
            Mock(team_id=200, current_elo_rating=1550)
        ]
        self.mock_db.query.return_value.all.return_value = mock_teams

        ratings = self.service.get_current_team_ratings()

        assert ratings == {100: 1650, 200: 1550}
        self.mock_db.query.assert_called_with(Team)

    def test_get_race_results_for_race(self):
        """Test getting race results for a specific race."""
        mock_results = [
            Mock(driver_id=1, final_position=1),
            Mock(driver_id=2, final_position=2),
            Mock(driver_id=3, final_position=3)
        ]

        # Set up query chain
        query = Mock()
        filter_result = Mock()
        order_result = Mock()

        query.filter.return_value = filter_result
        filter_result.order_by.return_value = order_result
        order_result.all.return_value = mock_results

        self.mock_db.query.return_value = query

        results = self.service.get_race_results_for_race(race_id=100)

        assert results == mock_results
        self.mock_db.query.assert_called_with(RaceResult)
        query.filter.assert_called_once()

    def test_get_completed_races_chronologically(self):
        """Test getting completed races in chronological order."""
        mock_races = [
            Mock(race_id=100, race_date=date(2024, 1, 1)),
            Mock(race_id=101, race_date=date(2024, 2, 1))
        ]

        # Set up query chain
        query = Mock()
        filter_result = Mock()
        order_result = Mock()

        query.filter.return_value = filter_result
        filter_result.order_by.return_value = order_result
        order_result.all.return_value = mock_races

        self.mock_db.query.return_value = query

        races = self.service.get_completed_races_chronologically()

        assert races == mock_races
        self.mock_db.query.assert_called_with(Race)

    def test_get_completed_races_with_season_filter(self):
        """Test getting completed races filtered by season."""
        mock_races = [Mock(race_id=100)]

        # Set up query chain
        query = Mock()
        filter1_result = Mock()
        filter2_result = Mock()
        order_result = Mock()

        query.filter.return_value = filter1_result
        filter1_result.filter.return_value = filter2_result
        filter2_result.order_by.return_value = order_result
        order_result.all.return_value = mock_races

        self.mock_db.query.return_value = query

        races = self.service.get_completed_races_chronologically(season_year=2024)

        assert races == mock_races
        assert filter1_result.filter.called

    def test_get_completed_races_with_limit(self):
        """Test getting completed races with limit."""
        mock_races = [Mock(race_id=100)]

        # Set up query chain
        query = Mock()
        filter_result = Mock()
        order_result = Mock()
        limit_result = Mock()

        query.filter.return_value = filter_result
        filter_result.order_by.return_value = order_result
        order_result.limit.return_value = limit_result
        limit_result.all.return_value = mock_races

        self.mock_db.query.return_value = query

        races = self.service.get_completed_races_chronologically(limit=10)

        assert races == mock_races
        order_result.limit.assert_called_with(10)

    @patch.object(ELOService, 'get_race_results_for_race')
    @patch.object(ELOService, 'get_current_driver_ratings')
    @patch.object(ELOService, 'get_current_team_ratings')
    def test_update_ratings_for_race(self, mock_team_ratings, mock_driver_ratings, mock_race_results):
        """Test updating ratings for a single race."""
        # Mock data
        mock_race_results.return_value = [
            Mock(race_id=100, driver_id=1, team_id=100, final_position=1, status=ResultStatus.FINISHED),
            Mock(race_id=100, driver_id=2, team_id=200, final_position=2, status=ResultStatus.FINISHED)
        ]
        mock_driver_ratings.return_value = {1: 1500, 2: 1500}
        mock_team_ratings.return_value = {100: 1500, 200: 1500}

        # Mock database updates
        self.service._apply_driver_updates = Mock()
        self.service._apply_team_updates = Mock()

        driver_updates, team_updates = self.service.update_ratings_for_race(100)

        # Should call calculation methods
        mock_race_results.assert_called_with(100)
        mock_driver_ratings.assert_called_once()
        mock_team_ratings.assert_called_once()

        # Should apply updates
        self.service._apply_driver_updates.assert_called_once()
        self.service._apply_team_updates.assert_called_once()

        # Should return updates
        assert isinstance(driver_updates, dict)
        assert isinstance(team_updates, dict)

    def test_update_ratings_for_race_empty_results(self):
        """Test updating ratings when no race results exist."""
        with patch.object(self.service, 'get_race_results_for_race', return_value=[]):
            driver_updates, team_updates = self.service.update_ratings_for_race(100)

            assert driver_updates == {}
            assert team_updates == {}

    def test_apply_driver_updates(self):
        """Test applying driver rating updates to database."""
        from ml.elo_calculator import ELORatingUpdate

        # Mock driver
        mock_driver = Mock()
        mock_driver.current_elo_rating = 1500

        query_result = Mock()
        query_result.filter.return_value.first.return_value = mock_driver
        self.mock_db.query.return_value = query_result

        updates = {
            1: ELORatingUpdate(
                entity_id=1,
                entity_type="driver",
                old_rating=1500,
                new_rating=1520,
                rating_change=20,
                race_id=100,
                final_position=1,
                expected_position=3.0
            )
        }

        self.service._apply_driver_updates(updates)

        # Should update the driver's rating
        assert mock_driver.current_elo_rating == 1520

    def test_apply_team_updates(self):
        """Test applying team rating updates to database."""
        from ml.elo_calculator import ELORatingUpdate

        # Mock team
        mock_team = Mock()
        mock_team.current_elo_rating = 1500

        query_result = Mock()
        query_result.filter.return_value.first.return_value = mock_team
        self.mock_db.query.return_value = query_result

        updates = {
            100: ELORatingUpdate(
                entity_id=100,
                entity_type="team",
                old_rating=1500,
                new_rating=1520,
                rating_change=20,
                race_id=100,
                final_position=1,
                expected_position=2.0
            )
        }

        self.service._apply_team_updates(updates)

        # Should update the team's rating
        assert mock_team.current_elo_rating == 1520

    def test_reset_all_ratings_to_base(self):
        """Test resetting all ratings to base rating."""
        # Mock query updates
        driver_query = Mock()
        team_query = Mock()

        def mock_query(model):
            if model == Driver:
                return driver_query
            elif model == Team:
                return team_query

        self.mock_db.query.side_effect = mock_query

        self.service._reset_all_ratings_to_base()

        # Should update all driver and team ratings
        driver_query.update.assert_called_once()
        team_query.update.assert_called_once()

    @patch.object(ELOService, 'get_completed_races_chronologically')
    @patch.object(ELOService, 'get_race_results_for_race')
    @patch.object(ELOService, 'get_current_driver_ratings')
    @patch.object(ELOService, 'get_current_team_ratings')
    @patch.object(ELOService, '_reset_all_ratings_to_base')
    @patch.object(ELOService, '_apply_final_ratings')
    def test_recalculate_all_ratings(self, mock_apply_final, mock_reset, mock_team_ratings,
                                   mock_driver_ratings, mock_race_results, mock_completed_races):
        """Test recalculating all ratings from scratch."""
        # Mock data
        mock_completed_races.return_value = [Mock(race_id=100), Mock(race_id=101)]
        mock_race_results.side_effect = [
            [Mock(race_id=100, driver_id=1, team_id=100)],
            [Mock(race_id=101, driver_id=1, team_id=100)]
        ]
        mock_driver_ratings.return_value = {1: 1500}
        mock_team_ratings.return_value = {100: 1500}

        final_driver_ratings, final_team_ratings = self.service.recalculate_all_ratings()

        # Should reset ratings
        mock_reset.assert_called_once()

        # Should get completed races
        mock_completed_races.assert_called_with(None)

        # Should apply final ratings
        mock_apply_final.assert_called_once()

        # Should return final ratings
        assert isinstance(final_driver_ratings, dict)
        assert isinstance(final_team_ratings, dict)

    def test_get_driver_rankings(self):
        """Test getting driver rankings."""
        mock_drivers = [
            Mock(driver_id=1, current_elo_rating=1600),
            Mock(driver_id=2, current_elo_rating=1500)
        ]

        # Set up query chain
        query = Mock()
        order_result = Mock()
        limit_result = Mock()

        query.order_by.return_value = order_result
        order_result.limit.return_value = limit_result
        limit_result.all.return_value = mock_drivers

        self.mock_db.query.return_value = query

        rankings = self.service.get_driver_rankings(limit=10)

        assert rankings == mock_drivers
        self.mock_db.query.assert_called_with(Driver)
        order_result.limit.assert_called_with(10)

    def test_get_team_rankings(self):
        """Test getting team rankings."""
        mock_teams = [
            Mock(team_id=100, current_elo_rating=1650),
            Mock(team_id=200, current_elo_rating=1550)
        ]

        # Set up query chain
        query = Mock()
        order_result = Mock()
        limit_result = Mock()

        query.order_by.return_value = order_result
        order_result.limit.return_value = limit_result
        limit_result.all.return_value = mock_teams

        self.mock_db.query.return_value = query

        rankings = self.service.get_team_rankings(limit=5)

        assert rankings == mock_teams
        self.mock_db.query.assert_called_with(Team)
        order_result.limit.assert_called_with(5)

    def test_get_driver_rating_history_placeholder(self):
        """Test getting driver rating history (placeholder implementation)."""
        mock_driver = Mock(driver_id=1, current_elo_rating=1600)

        query_result = Mock()
        query_result.filter.return_value.first.return_value = mock_driver
        self.mock_db.query.return_value = query_result

        history = self.service.get_driver_rating_history(1)

        assert len(history) == 1
        assert history[0]["driver_id"] == 1
        assert history[0]["current_rating"] == 1600
        assert "not yet implemented" in history[0]["note"]

    def test_get_driver_rating_history_not_found(self):
        """Test getting rating history for non-existent driver."""
        query_result = Mock()
        query_result.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = query_result

        history = self.service.get_driver_rating_history(999)

        assert history == []

    def test_predict_race_outcome_with_driver_ids(self):
        """Test predicting race outcome with specific driver IDs."""
        mock_drivers = [
            Mock(driver_id=1, driver_name="Driver 1", current_elo_rating=1600),
            Mock(driver_id=2, driver_name="Driver 2", current_elo_rating=1500)
        ]

        query_result = Mock()
        query_result.filter.return_value.all.return_value = mock_drivers
        self.mock_db.query.return_value = query_result

        predictions = self.service.predict_race_outcome(100, [1, 2])

        assert len(predictions) == 2
        assert predictions[0]["driver_id"] == 1  # Higher rated should be first
        assert predictions[0]["win_probability"] > predictions[1]["win_probability"]
        assert all("win_probability" in pred for pred in predictions)

    def test_predict_race_outcome_all_drivers(self):
        """Test predicting race outcome for all drivers."""
        mock_drivers = [
            Mock(driver_id=1, driver_name="Driver 1", current_elo_rating=1500),
            Mock(driver_id=2, driver_name="Driver 2", current_elo_rating=1600)
        ]

        query_result = Mock()
        query_result.all.return_value = mock_drivers
        self.mock_db.query.return_value = query_result

        predictions = self.service.predict_race_outcome(100)

        assert len(predictions) == 2
        # Should be sorted by rating (descending)
        assert predictions[0]["current_elo_rating"] >= predictions[1]["current_elo_rating"]

    def test_predict_race_outcome_empty_drivers(self):
        """Test predicting race outcome with no drivers."""
        query_result = Mock()
        query_result.all.return_value = []
        self.mock_db.query.return_value = query_result

        predictions = self.service.predict_race_outcome(100)

        assert predictions == []

    def test_factory_function(self):
        """Test the factory function."""
        mock_db = Mock()
        service = get_elo_service(mock_db)

        assert isinstance(service, ELOService)
        assert service.db == mock_db
        assert service.calculator.k_factor == 32

        service_custom = get_elo_service(mock_db, k_factor=24)
        assert service_custom.calculator.k_factor == 24


class TestELOServiceIntegration:
    """Integration-style tests for ELO service."""

    def test_end_to_end_rating_calculation(self):
        """Test end-to-end rating calculation workflow."""
        mock_db = Mock()
        service = ELOService(mock_db)

        # Mock the complete workflow
        with patch.object(service, 'get_race_results_for_race') as mock_results, \
             patch.object(service, 'get_current_driver_ratings') as mock_driver_ratings, \
             patch.object(service, 'get_current_team_ratings') as mock_team_ratings, \
             patch.object(service, '_apply_driver_updates') as mock_apply_drivers, \
             patch.object(service, '_apply_team_updates') as mock_apply_teams:

            # Set up realistic mock data
            mock_results.return_value = [
                Mock(race_id=100, driver_id=1, team_id=100, final_position=1, status=ResultStatus.FINISHED),
                Mock(race_id=100, driver_id=2, team_id=200, final_position=2, status=ResultStatus.FINISHED)
            ]
            mock_driver_ratings.return_value = {1: 1500, 2: 1500}
            mock_team_ratings.return_value = {100: 1500, 200: 1500}

            # Run the calculation
            driver_updates, team_updates = service.update_ratings_for_race(100)

            # Verify the workflow
            assert mock_results.called
            assert mock_driver_ratings.called
            assert mock_team_ratings.called
            assert mock_apply_drivers.called
            assert mock_apply_teams.called

            # Verify updates were generated
            assert len(driver_updates) == 2
            assert len(team_updates) == 2