USE vrp_system;

UPDATE USER SET password='$2b$12$.3kmlHLupvVysjttLybf.u1Y1ty4Mmdidz8yXvJIY/YUxca5ZpKoW';

SELECT username, LEFT(password, 20) as password_preview FROM USER;
